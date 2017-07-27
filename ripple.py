#
#   Rippler - ripple.py - main code for operations
#

#   The Rippler project,
#   Copyright (c) Ashutosh Verma 2017
#       (https://levodex.com/, https://github.com/levodex/)
#   All rights reserved
#   
#
#
#   Parts of this software make use of additional open source components under a different license
#   Please check additional licenses
#   
#
#
#   TODO: Write doc entries for basic architecture design used here (ripple.py)
#
#


#
#	Main definitions for ripple
#

import io
import re
import pymongo
import random
import blowfish
import os
import binascii
import base64
import uuid
import struct
import qrcode
import qrtools
import subprocess
import gridfs
import hashlib
import zlib
import pickle


#
#   Currently due to time constraints zBar libraries havent been merged into the application base
#   and all derivatives of this version of project will need to implement their equivalent locally before building
#       (See known issuee)
#
#   TODO: Merge QR library in the codebase instead of using an external binary (duplicate with daemon.py)
#


from pymongo import MongoClient
from base64 import b64encode
from base64 import b64decode
from os import urandom
from bson.regex import Regex
from subprocess import call
from io import StringIO
from io import BytesIO
from bson.int64 import Int64

#	Container class for Debugging

class Base(object):
	con = {}
	req = {}
	def __init__(self):
		self.con = MongoClient()
		self.req = self.con['ripple']
		self.seq = self.con['session']
	def rebuild_raw(self):
		self.con.drop_database('session')
	def rebuild_base(self):
		self.req.drop_collection('ripples')
		self.req.create_collection('ripples')
		self.req.drop_collection('splashes')
		self.req.create_collection('splashes')
	def rebuild_filters(self):
		self.req.drop_collection('filters')
		self.req.create_collection('filters')
	def add_filter(self, filter, words):
		f = self.req['filters']
		d = {}
		r = f.find({filter: {"$exists": True}}).limit(1)
		w = []
		for x in r:
			w.append(x)
		if(len(w) is not 0):
			d[filter] = w[0][filter]
		else:
			d[filter] = []
		for x in words:
			if((len(w) is 0) or (x not in w[0][filter])):
				d[filter].append(x)
		f.replace_one({filter: {"$exists": True}}, d, True)
	def dump(self):
		print("-Base dump-")
		print("-Ripple dump-")
		for x in self.req['ripples'].find({}, {'_id':False}):
			print(x)
		print("-Splashes dump-")
		for x in self.req['splashes'].find({}, {'_id':False}):
			print(x)
		print("-Raw dump-")
		g = gridfs.GridFS(self.seq, 'sessions')
		for x in self.seq['sessions'].find({}, {'_id':False}):
			print(x)
		for x in g.list():
			if(g.exists(x)):
				print(x)
		print("-Filter dump-")
		for x in self.req['filters'].find({}, {'_id':False}):
			print(x)
#

#	Wrapper class for BlowFish

class CryptoWrapper(object):
	cipher = ""
	vector = ""
	def __init__(self, hash):
		self.cipher = blowfish.Cipher(bytes(hash, "utf8"))
		self.vector = urandom(8)
	def getcode(self):
		return self.vector
	def setcode(self, data):
		self.vector = data
	def encrypt(self, data):
		return binascii.hexlify(b"".join(self.cipher.encrypt_ofb(bytes(data, "utf8"), self.vector)))
	def decrypt(self, data):
		return (b"".join(self.cipher.decrypt_ofb(binascii.unhexlify(data), self.vector))).decode("utf8")
#

#	Wrapper class for Filtering

class ContentFilter(object):
	fil = {}
	def __init__(self):
		con = MongoClient()
		req = con['ripple']
		d = req['filters'].find({}, {'_id':False})
		x = y = z = {}
		for x in d:
			for y in x:
				self.fil[y] = []
				for z in x[y]:
					self.fil[y].append(z)
	def bare(self, s):
		t = re.sub('[\,\.\:\;\'\"\?\\\/\!\@\#\$\%\^\&\*\(\)\-\+\=\<\>\[\]\{\}\|]', ' ', s)
		return t.lower()
	def filter(self, title, content, tags):
		f = {}
		a = self.bare(title).split()
		b = self.bare(content).split()
		c = tags.lower().split(',')
		for x in a:
			for y in self.fil:
				if(x in self.fil[y]):
					f[y] = True
		for x in b:
			for y in self.fil:
				if(x in self.fil[y]):
					f[y] = True
		for x in c:
			for y in self.fil:
				if(x in self.fil[y]):
					f[y] = True
		return f
#

#	Wrapper class for Volatile Storage Session

class VolatileSession(object):
	con = None
	req = None
	gfs = None
	obj = None
	fnm = None
	rwm = None
	seq = None
	fid = None
	atm = None
	def seqnext(self):
		r = None
		try:
			r = str(self.seq.find_one_and_update( filter = { '_id': 'sessseq' }, update = { '$inc': {'seq': Int64(1)}}, projection = {'_id': False} ).get('seq'))
		except Exception as ex:
			self.req['sessions'].insert({'_id': "sessseq", 'seq': Int64(0)})
			r = str(self.seq.find_one_and_update( filter = { '_id': 'sessseq' }, update = { '$inc': {'seq': Int64(1)}}, projection = {'_id': False} ).get('seq'))
		return r
	def __enter__(self):
		if( self.rwm == 'w' ):
			self.obj = self.gfs.open_upload_stream( self.fnm, None, metadata={'attempts': self.atm} )
			self.fid = self.obj._id
		elif( self.rwm == 'c' ):
			g = gridfs.GridFS(self.req, 'sessions')
			self.fid = g.put( b"", filename = self.fnm )
			self.obj = self.gfs.open_upload_stream( self.fnm, None, metadata={'attempts': self.atm} )
		elif( self.rwm == 'r' ):
			self.obj = self.gfs.open_download_stream_by_name( self.fnm )
			self.fid = self.obj._id
			try:
				self.atm = self.obj.metadata['attempts']
			except Exception as ex:
				self.atm = 2
		elif( self.rwm == 'd' ):
			self.obj = self.gfs.open_download_stream_by_name( self.fnm )
			self.fid = self.obj._id
			try:
				self.atm = self.obj.metadata['attempts']
			except Exception as ex:
				self.atm = 2
		elif( self.rwm == 'n' ):
			self.fnm = str( self.seqnext() )
			g = gridfs.GridFS(self.req, 'sessions')
			self.fid = g.put( b"", filename = self.fnm )
			self.obj = self.gfs.open_upload_stream( self.fnm, None, metadata={'attempts': self.atm} )
		return self
	def __init__(self, rawhead, _fn=None, _fm='n', _fa=2):
		self.con = rawhead
		self.fnm = _fn
		self.rwm = _fm
		self.atm = _fa
		self.req = self.con['session']
		if('sessions' not in self.req.collection_names()):
			self.req.create_collection('sessions')
			self.req['sessions'].insert({'_id': "sessseq", 'seq': Int64(0)})
		self.seq = self.req['sessions']
		self.gfs = gridfs.GridFSBucket(self.req, 'sessions')
	def __exit__(self, type, value, traceback):
		if(self.obj is not None):
			self.obj.close()
			self.obj = None
		if( (self.rwm == 'r') and (self.fid is not None) ):
			g = gridfs.GridFS(self.req, 'sessions')
			g.delete(self.fid)
			self.fid = None
		elif(self.rwm == 'd'):
			if( (self.atm is 0) and (self.fid is not None) ):
				g = gridfs.GridFS(self.req, 'sessions')
				g.delete(self.fid)
				self.fid = None
			else:
				self.atm = self.atm - 1
				self.obj = self.gfs.open_upload_stream( self.fnm, None, metadata={'attempts': self.atm} )
				self.obj.close()
		self.seq.reindex()
		#self.con.close()
	def getref(self):
		return self.fnm
	def open(self, _fm=None):
		try:
			if(_fm is None):
				_fm = self.rwm
			if( _fm == 'w' or _fm == 'c' or _fm == 'n' ):
				self.obj = self.gfs.open_upload_stream( self.fnm )
				self.rwm = _fm
			elif( _fm == 'r' ):
				self.obj = self.gfs.open_download_stream_by_name( self.fnm )
				self.rwm = _fm
		except Exception as ex:
			return None
		return self.obj
	def close(self):
		self.obj.close()
		self.obj = None
#

#	Container class for Ripples
class Ripple(object):
	con = None
	req = None
	def seqnext(self):
		r = None
		try:
			r = self.req['ripples'].find_one_and_update( filter = { '_id': 'rippleseq' }, update = { '$inc': {'seq': Int64(1)}}, projection = {'_id': False} ).get('seq')
		except Exception as ex:
			self.req['ripples'].insert({'_id': "rippleseq", 'seq': Int64(0)})
			r = self.req['ripples'].find_one_and_update( filter = { '_id': 'rippleseq' }, update = { '$inc': {'seq': Int64(1)}}, projection = {'_id': False} ).get('seq')
		return r
	def __init__(self, rawhead):
		self.con = rawhead
		self.req = self.con['ripple']
	def __enter__(self):
		r = self.con
		f = self.req
		self.con = MongoClient()
		self.req = self.con['ripple']
		if('ripples' not in self.req.collection_names()):
			self.req.create_collection('ripples')
			self.req['ripples'].insert({'_id': "rippleseq", 'seq': Int64(0)})
		if('splashes' not in self.req.collection_names()):
			self.req.create_collection('splashes')
		self.con.close()
		self.req = f
		self.con = r
		return self
	def __exit__(self, type, value, traceback):
		self.con.close()
		self.req = None
		self.con = None
	def create(self, title, content, tags, _ffv=True, _fc=False, _fmo=False, _fenc=False, _pkey=None):
		r = self.req['ripples']
		s = self.req['splashes']
		c = self.seqnext()
		d = {}
		u = uuid.uuid1(None, c).hex
		l = list()
		for x in s.find({'crest':u}):
			l.append(x)
		while(len(l) is not 0):
			u = uuid.uuid1(None, c).hex
			l = []
			for x in s.find({'crest':u}):
				l.append(x)
		d['crest'] = u
		t = b64encode(urandom(42)).decode('utf-8')
		t = t[:56]
		w = CryptoWrapper(t)
		d['trough'] = b64encode(w.encrypt("%d" % (c))).decode('utf-8') + "_" + b64encode(w.getcode()).decode('utf-8')
		l = list()
		l.append(d['crest'])
		l.append(t)
		s.insert_one(d)
		u = {}
		f = ContentFilter()
		t = tags.split(',')
		u['tags'] = t
		u['filters'] = f.filter(title, content, tags)
		d = {}
		u['id'] = c
		if( (_fenc is True) and (_pkey is not None) and (len(_pkey) is not 0) ):
			w = CryptoWrapper(_pkey[:56])
			w.setcode( str(c).encode() )
			u['content'] = w.encrypt(content).decode('utf-8')
		else:
			u['content'] = content
		u['title'] = title
		d['feedback_visible'] = _ffv
		d['commercial'] = _fc
		d['member_only'] = _fmo
		d['encrypted'] = _fenc
		d['num_read'] = 0
		u['flags'] = d
		u['links'] = list()
		r.insert_one(u)
		l = '_'.join(l)
		q = qrcode.make(l)
		r = None
		with VolatileSession(self.con) as sesshead:
			q.save(sesshead.open())
			r = sesshead.getref()
		return r
	def modify(self, sessref, title, content, tags, _ffv=True, _fc=False, _fmo=False, _fenc=False, _pkey=None):
		l = list()
		q = None
		r = None
		e = None
		f = None
		s = None
		t = None
		try:
			with VolatileSession(self.con, str(sessref), 'r') as e:
				with VolatileSession(self.con, str(sessref) + ".txt", 'c') as f:
					s = e.open().read()
					if(len(s) is 0):
						return False
					else:
						t = StringIO()
					q = subprocess.Popen(["zbarimg", "PNG:-", "-q"], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
					q.stdin.write(s)
					q.stdin.close()
					q.wait()
					if(q.returncode is not 0):
						return False
					else:
						t = q.stdout.read()
						s = f.open()
						s.write(t)
						s.close()
						s = f.open('r')
						s = s.read().decode('utf-8')
						l = s.split('\n')
						l = l[0].split(':')
						if( l[0] is not 'ERROR' ):
							l = l[1].split('_')
							l = self.unsplash(l[0][:56], l[1][:56])
						else:
							return False
		except Exception as ex:
			return False
		if( l is None ):
			return False
		r = self.req['ripples']
		s = self.req['splashes']
		u = l
		c = u['id']
		f = ContentFilter()
		t = tags.split(',')
		u['tags'] = t
		u['filters'] = f.filter(title, content, tags)
		d = {}
		if( (_fenc is True) and (_pkey is not None) and (len(_pkey) is not 0) ):
			w = CryptoWrapper(_pkey[:56])
			w.setcode( str(c).encode() )
			u['content'] = w.encrypt(content).decode('utf-8')
		else:
			u['content'] = content
		u['title'] = title
		d['feedback_visible'] = _ffv
		d['commercial'] = _fc
		d['member_only'] = _fmo
		d['num_read'] = 0
		d['encrypted'] = _fenc
		u['flags'] = d
		r.replace_one({'id':c}, u)
		return True
	def find(self, ftitle, fcontent, ftags, _fc=False, _fmo=False):
		r = self.req['ripples']
		l = list()
		u = {}
		x = {}
		if(len(ftags) > 0):
			t = ftags.split(',')
			u['tags'] = t
		if(len(ftitle) > 0):
			x = Regex.from_native( re.compile(ftitle + '*', re.IGNORECASE) )
			u['title'] = x
		if(len(fcontent) > 0):
			x = Regex.from_native( re.compile(fcontent + '*', re.IGNORECASE) )
			u['content'] = x
		f = {}
		for i in r.find(u, {'_id':False}):
			if( ('flags' in i) and ( _fc == i['flags']['commercial']) and ( _fmo == i['flags']['member_only']) and (i['flags']['encrypted'] is False) ):
				f = i
				l.append(f)
		if( len(l) is 0 ):
			return []
		return l
	def interlink(self, sessref_base, sessref_link, _fd=False):
		l = list()
		q = None
		r = None
		e = None
		f = None
		s = None
		t = None
		try:
			if(_fd is True):
				with VolatileSession(self.con, str(sessref_base), 'd') as e:
					with VolatileSession(self.con, str(sessref_base) + ".txt", 'c') as f:
						s = e.open().read()
						if(len(s) is 0):
							return False
						else:
							t = StringIO()
						q = subprocess.Popen(["zbarimg", "PNG:-", "-q"], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
						q.stdin.write(s)
						q.stdin.close()
						q.wait()
						if(q.returncode is not 0):
							return False
						else:
							t = q.stdout.read()
							s = f.open()
							s.write(t)
							s.close()
							s = f.open('r')
							s = s.read().decode('utf-8')
							l = s.split('\n')
							l = l[0].split(':')
							if( l[0] is not 'ERROR' ):
								l = l[1].split('_')
								l = self.unsplash(l[0][:56], l[1][:56])
							else:
								return False
			else:
				with VolatileSession(self.con, str(sessref_base), 'r') as e:
					with VolatileSession(self.con, str(sessref_base) + ".txt", 'c') as f:
						s = e.open().read()
						if(len(s) is 0):
							return False
						else:
							t = StringIO()
						q = subprocess.Popen(["zbarimg", "PNG:-", "-q"], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
						q.stdin.write(s)
						q.stdin.close()
						q.wait()
						if(q.returncode is not 0):
							return False
						else:
							t = q.stdout.read()
							s = f.open()
							s.write(t)
							s.close()
							s = f.open('r')
							s = s.read().decode('utf-8')
							l = s.split('\n')
							l = l[0].split(':')
							if( l[0] is not 'ERROR' ):
								l = l[1].split('_')
								l = self.unsplash(l[0][:56], l[1][:56])
							else:
								return False
		except Exception as ex:
			return False
		if( l is None ):
			return False
		a = l
		try:
			if(_fd is True):
				with VolatileSession(self.con, str(sessref_link), 'd') as e:
					with VolatileSession(self.con, str(sessref_link) + ".txt", 'c') as f:
						s = e.open().read()
						if(len(s) is 0):
							return False
						else:
							t = StringIO()
						q = subprocess.Popen(["zbarimg", "PNG:-", "-q"], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
						q.stdin.write(s)
						q.stdin.close()
						q.wait()
						if(q.returncode is not 0):
							return False
						else:
							t = q.stdout.read()
							s = f.open()
							s.write(t)
							s.close()
							s = f.open('r')
							s = s.read().decode('utf-8')
							l = s.split('\n')
							l = l[0].split(':')
							if( l[0] is not 'ERROR' ):
								l = l[1].split('_')
								l = self.unsplash(l[0][:56], l[1][:56])
							else:
								return False
			else:
				with VolatileSession(self.con, str(sessref_link), 'r') as e:
					with VolatileSession(self.con, str(sessref_link) + ".txt", 'c') as f:
						s = e.open().read()
						if(len(s) is 0):
							return False
						else:
							t = StringIO()
						q = subprocess.Popen(["zbarimg", "PNG:-", "-q"], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
						q.stdin.write(s)
						q.stdin.close()
						q.wait()
						if(q.returncode is not 0):
							return False
						else:
							t = q.stdout.read()
							s = f.open()
							s.write(t)
							s.close()
							s = f.open('r')
							s = s.read().decode('utf-8')
							l = s.split('\n')
							l = l[0].split(':')
							if( l[0] is not 'ERROR' ):
								l = l[1].split('_')
								l = self.unsplash(l[0][:56], l[1][:56])
							else:
								return False
		except Exception as ex:
			return False
		if( l is None ):
			return False
		b = l
		r = self.req['ripples']
		s = self.req['splashes']
		c = a['id']
		d = b['id']
		if( c == d ):
			return False
		elif(d not in a['links']):
			a['links'].append(d)
		if(c not in b['links']):
			b['links'].append(c)
		r.replace_one({'id':c}, a)
		r.replace_one({'id':d}, b)
		return [c, d]
	def readpost(self, rippleid):
		r = self.req['ripples']
		u = {}
		s = None
		try:
			u['id'] = int(rippleid)
			f = {}
			s = r.find_one( filter = u, projection = {'_id' : False} )
			f = s['flags']
			f['num_read'] = f['num_read'] + 1
			s['flags'] = f
			s = r.find_one_and_replace( filter = u, replacement = s, projection = {'_id' : False}, sort = None, return_document = pymongo.collection.ReturnDocument.AFTER )
		except Exception as ex:
			s = None
		return s
	def openpost(self, sessref, _pkey=''):
		l = list()
		q = None
		r = None
		e = None
		f = None
		s = None
		t = None
		try:
			with VolatileSession(self.con, str(sessref), 'r') as e:
				with VolatileSession(self.con, str(sessref) + ".txt", 'c') as f:
					s = e.open().read()
					if(len(s) is 0):
						return None
					else:
						t = StringIO()
					q = subprocess.Popen(["zbarimg", "PNG:-", "-q"], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
					q.stdin.write(s)
					q.stdin.close()
					q.wait()
					if(q.returncode is not 0):
						return None
					else:
						t = q.stdout.read()
						s = f.open()
						s.write(t)
						s.close()
						s = f.open('r')
						s = s.read().decode('utf-8')
						l = s.split('\n')
						l = l[0].split(':')
						if( l[0] is not 'ERROR' ):
							l = l[1].split('_')
							l = self.unsplash(l[0][:56], l[1][:56])
						else:
							return None
		except Exception as ex:
			return None
		if( l is None ):
			return None
		r = self.req['ripples']
		s = self.req['splashes']
		u = l
		c = u['id']
		if(u['flags']['encrypted'] is True):
			if( len(_pkey) is not 0 ):
				w = CryptoWrapper(_pkey[:56])
				w.setcode( str(c).encode() )
				try:
					u['content'] = str(w.decrypt( u['content'] ))
				except Exception as ex:
					return None
			else:
				return None
		return u
	def unsplash(self, crest, trough):
		r = self.req['ripples']
		s = self.req['splashes']
		d = {}
		d['crest'] = crest
		f = None
		l = 0
		for i in s.find(d, {'_id':False}):
			f = i
			l = l + 1
		if( l == 0 ):
			return None
		f['trough']= f['trough'].split('_')
		t = b64decode(f['trough'][0])
		f = b64decode(f['trough'][1])
		c = f
		w = CryptoWrapper(trough)
		w.setcode(c)
		f = list()
		d = {}
		try:
			d['id'] = int(w.decrypt(t))
		except Exception as ex:
			return None
		for i in r.find(d, {'_id':False}):
			f.append(i)
		f = f[0]
		return f
#

#
#
# TODO: Journalling code must be moved to separate file and refrenced here since this is an experimental feature
#
#


#	Container class for Journals
class Journal(object):
	con = None
	req = None
	gfs = None
	gfb = None
	obj = None
	jid = None
	jnm = None
	key = None
	jdc = None
	def seqnext(self):
		r = None
		try:
			r = self.req['journals'].find_one_and_update( filter = { '_id': 'journalseq' }, update = { '$inc': {'seq': Int64(1)}}, projection = {'_id': False} ).get('seq')
		except Exception as ex:
			self.req['journals'].insert({'_id': "journalseq", 'seq': Int64(0)})
			r = self.req['journals'].find_one_and_update( filter = { '_id': 'journalseq' }, update = { '$inc': {'seq': Int64(1)}}, projection = {'_id': False} ).get('seq')
		r = str(r).encode()
		h = zlib.crc32(r)
		r = binascii.hexlify(str(h).encode() + '-'.encode() + r).decode('utf-8')
		return r
	def __init__(self, rawhead, key):
		self.con = rawhead
		self.req = self.con['journal']
		self.gfs = gridfs.GridFS(self.req, 'journals')
		self.gfb = gridfs.GridFSBucket(self.req, 'journals')
		self.key = key
	def __enter__(self):
		r = self.con
		f = self.req
		self.con = MongoClient()
		self.req = self.con['journal']
		if('journals' not in self.req.collection_names()):
			self.req.create_collection('journals')
			self.req['journals'].insert({'_id': "journalseq", 'seq': Int64(0)})
		self.con.close()
		self.req = f
		self.con = r
		return self
	def __exit__(self, type, value, traceback):
		self.con.close()
		self.req = None
		self.con = None
	def new(self):
		self.jnm = self.seqnext()
		self.jid = self.gfs.put( b"", filename = self.jnm )
	def build(self, _buffer):
		self.jnm = self.getjname(_buffer)
		if( self.jnm is not None ):
			try:
				self.obj = self.gfs.get_version( self.jnm, -1, metadata={'key': self.key} )
				self.jid = self.obj._id
			except Exception as ex:
				self.obj = None
				self.jid = None
	def load(self):
		if( self.jnm is not None ):
			try:
				self.obj = self.gfs.get_version( self.jnm, -1, metadata={'key': self.key} )
			except Exception as ex:
				self.jdc = None
			self.jdc = pickle.load(self.obj)
		else:
			self.jdc = None
		self.obj.close()
		return self.jdc
	def save(self):
		if( self.jnm is not None ):
			try:
				self.obj = self.gfb.open_upload_stream( self.jnm, None, metadata={'key': self.key} )
				pickle.dump(self.jdc, self.obj)
			except Exception as ex:
				return False
		else:
			return False
		self.obj.close()
		return True
	def add(self):
		if( self.jdc is None ):
			self.jdc = list()
			self.jdc.append()
		else:
			pass
	def getjname(self, buffer):
		q = None
		s = None
		l = None
		try:
			q = subprocess.Popen(["zbarimg", "PNG:-", "-q"], stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
			q.stdin.write(buffer)
			q.stdin.close()
			q.wait()
			if(q.returncode is not 0):
				return None
			else:
				t = q.stdout.read()
				s = t.decode('utf-8')
				l = s.split('\n')
				l = l[0].split(':')
				if( l[0] is not 'ERROR' ):
					l = l[1]
				else:
					return None
		except Exception as ex:
			return None
		return l
#
