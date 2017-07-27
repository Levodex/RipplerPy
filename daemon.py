#
#   Rippler - daemon.py - main daemon for web server
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
#   TODO: Write doc entries for control flow
#
#

import ripple
import cherrypy
import pymongo
import json
import os


#
#   Currently due to time constraints zBar libraries havent been merged into the application base
#   and all derivatives of this version of project will need to implement their equivalent locally before building
#       (See known issues)
#
#   TODO: Merge QR library in the codebase instead of using an external binary (duplicate with ripple.py)
#


from pymongo import MongoClient
from base64 import b64encode

#
# TODO: work on ways to package in MongoDB eggs/installer MSIs alongside to make Rippler a standalone on production
#

from ripple import Ripple
from ripple import VolatileSession

def html_decode(s):
	s = json.dumps( s )
	s = s.replace("'", '&#39;')
	return s

# Client Request handler

class ClientRequest(object):
	@cherrypy.expose
	def index(self, login='', password=''):
		r = None
		if(login == 'ryuu' and password == 'ryuu'):
			raise cherrypy.HTTPRedirect('rippler')
		else:
			with open('static/index.html', 'rb') as f:
				r = f.read()
		return r
	@cherrypy.expose
	def rippler(self):
		r = None
		with open('static/rippler.html', 'rb') as f:
			r = f.read()
		return r
	@cherrypy.expose
	def read(self, id='', assoc=''):
		r = None
		f = None
		if( len(id) > 0 ):
			con = MongoClient()
			with Ripple(con) as r:
				a = r.readpost( int(id) )
				if( a is None):
					with open('static/http404.html', 'rb') as r:
						f = r.read()
					return f
				with open('static/read.html', 'rb') as r:
					f = r.read()
				f = f.decode('utf-8')
				l = '<script type="text/javascript">$(document).ready(function(){'
				l = l + '$("#stitle").html(\''+ html_decode(a['title'])  +'\');'
				l = l + '$("#scontents").html(\''+ html_decode(a['content'])  +'\');'
				l = l + '$("#stags").html(\'Tags: '
				for r in a['tags']:
					l = l + '<span class="stagslayer">' + html_decode(r) + '</span>'
				l = l +'\');'
				l = l + '$("#slinks").html(\'<a href="read?assoc='+ str(id)  +'">Associated Stories</a>\');'
				l = l + '});</script>'
				return f + l
		elif( len(assoc) > 0 ):
			con = MongoClient()
			with Ripple(con) as r:
				a = r.readpost( int(assoc) )
				if( a is None):
					with open('static/http404.html', 'rb') as r:
						f = r.read()
					return f
				with open('static/searchres.html', 'rb') as s:
					f = s.read()
				f = f.decode('utf-8')
				l = '<script type="text/javascript">$(document).ready(function(){'
				l = l + '$("#stitle").html(\''+ html_decode(a['title'])  +'\');'
				l = l + '$("#sflags").html(\'Associated stories: '
				l = l + '\');'
				l = l + '$("#scontents").html(\''
				i = 1
				x = None
				y = None
				if( len(a['links']) > 0 ):
					for x in a['links']:
						z = r.readpost( x )
						l = l + '<a href="read?id=' + str(z['id']) + '"><div class="slinkslayer">'+ str(i) +'. ' + html_decode(z['title'])
						for y in z['tags']:
							l = l + ' <span class="stagslayer">' + html_decode(y) + '</span>'
						l = l + ' </div></a>'
						i = i + 1
				else:
					l = l + 'No stories found'
				l = l +'\');'
				l = l + '});</script>'
				return f + l
		else:
			raise cherrypy.HTTPRedirect('search')
	@cherrypy.expose
	def search(self, qtitle='', qc='', qtags=''):
		r = None
		f = None
		if( len(qtitle) > 0 or len(qc) > 0 or len(qtags) > 0 ):
			con = MongoClient()
			with Ripple(con) as r:
				a = r.find( qtitle, qc, qtags )
				with open('static/searchres.html', 'rb') as r:
					f = r.read()
				f = f.decode('utf-8')
				l = '<script type="text/javascript">$(document).ready(function(){'
				l = l + '$("#sflags").html(\'Search for '
				if(len(qtitle) > 0):
					l = l + '"'+ html_decode(qtitle) +'"'
				if(len(qc) > 0):
					l = l + '"'+ html_decode(qc) +'"'
				if(len(qtags) > 0):
					l = l + '"'+ html_decode(qtags) +'"'
				l = l + ' in stories:\');'
				if(len(a) > 0):
					l = l + '$("#scontents").html(\''
					i = 1
					x = None
					y = None
					for x in a:
						l = l + '<a href="read?id=' + str(x['id']) + '"><div class="slinkslayer">'+ str(i) +'. ' + x['title']
						for y in x['tags']:
							l = l + ' <span class="stagslayer">' + html_decode(y) + '</span>'
						l = l + ' </div></a>'
						i = i + 1
					l = l +'\');'
				else:
					l = l + '$("#scontents").html(\''
					l = l + 'No stories found'
					l = l +'\');'
				l = l + '});</script>'
				return f + l
		else:
			with open('static/search.html', 'rb') as r:
				f = r.read()
			return f
	@cherrypy.expose
	def qr(self, sess=''):
		r = None
		f = None
		l = None
		con = MongoClient()
		try:
			with VolatileSession( con, sess, 'r') as r:
				l = r.open()
				if( l is None ):
					raise Exception()
				else:
					f = l.read()
					if( len(f) < 1 ):
						raise Exception()
					else:
						f = '<script type="text/javascript">$(document).ready(function(){$("#r2").html(\'<img id="qrimg" src="data:image/png;base64, ' + b64encode(f).decode('utf-8') + '" />\');});</script>'
						with open('static/qrdl.html', 'rb') as r:
							l = r.read()
				return l.decode('utf-8') + f
		except Exception as ex:
			with open('static/http410.html', 'rb') as r:
				f = r.read()
			return f
	@cherrypy.expose
	def write(self, qtitle='', qc='', qtags=''):
		r = None
		f = None
		l = None
		if( len(qtitle) > 0 and len(qc) > 0 ):
			con = MongoClient()
			with Ripple(con) as r:
				f = r.create( qtitle, qc, qtags )
			raise cherrypy.HTTPRedirect('qr?sess=' + f)
		else:
			with open('static/write.html', 'rb') as r:
				f = r.read()
			return f
	@cherrypy.expose
	@cherrypy.tools.json_out()
	def upload(self, qr1, qr2):
		con = MongoClient()
		l = None
		r = None
		try:
			with VolatileSession( con ) as new:
				size = 0
				l = new.open()
				while True:
					data = qr1.file.read(8192)
					if not data:
						break
					size += len(data)
					l.write(data)
				r = new.getref()
				l.close()
		except Exception as ex:
			raise cherrypy.HTTPRedirect('manage?sessfail=' + r)
		a = r
		r = None
		try:
			with VolatileSession( con ) as new:
				size = 0
				l = new.open()
				while True:
					data = qr2.file.read(8192)
					if not data:
						break
					size += len(data)
					l.write(data)
				r = new.getref()
				l.close()
		except Exception as ex:
			raise cherrypy.HTTPRedirect('manage?sessfail=' + r)
		b = r
		raise cherrypy.HTTPRedirect('manage?sessb=' + a + '&sessl=' + b)
	@cherrypy.expose
	def manage(self, sessfail='', sessb='', sessl=''):
		r = None
		if(len(sessfail) is not 0):
			with open('static/http400.html', 'rb') as f:
				r = f.read()
			return r
		elif( (len(sessb) is 0) or (len(sessl) is 0) ):
			with open('static/manage.html', 'rb') as f:
				r = f.read()
			return r
		if(True):
			con = MongoClient()
			with Ripple(con) as r:
				sessb = str(sessb)
				sessl = str(sessl)
				f = r.interlink( sessb, sessl, False )
				a = r.readpost( f[0] )
				b = r.readpost( f[1] )
				with open('static/update.html', 'rb') as r:
					f = r.read()
				f = f.decode('utf-8')
				l = '<script type="text/javascript">$(document).ready(function(){'
				l = l + '$("#stitle1").html(\''+ html_decode(a['title'])  +'\');'
				l = l + '$("#stitle2").html(\''+ html_decode(b['title'])  +'\');'
				l = l + '$("#scontents1").html(\''+ html_decode(a['content'])  +'\');'
				l = l + '$("#scontents2").html(\''+ html_decode(b['content'])  +'\');'
				l = l + '$("#stags1").html(\'Tags: '
				for r in a['tags']:
					l = l + '<span class="stagslayer">' + html_decode(r) + '</span>'
				l = l +'\');'
				l = l + '$("#stags2").html(\'Tags: '
				for r in b['tags']:
					l = l + '<span class="stagslayer">' + r + '</span>'
				l = l +'\');'
				l = l + '});</script>'
				return f + l
		else:
			raise cherrypy.HTTPRedirect('manage?sessfail=' + sessb)
#

#
#
#   TODO: Re-write code for Flask frameworking for future versions
#
#

#
if( __name__ == '__main__' ):
	cherrypy.quickstart(ClientRequest(), '/', 'daemonconfig.conf')
	cherrypy.config.update('daemonconfig.conf')