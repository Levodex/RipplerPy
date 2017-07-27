	(function()
		{
			$(document).ready(function()
			{
				$('#navbar').html
				(
					'<div class="col-xs-4 col-sm-4 col-md-3 col-lg-2"><div class="navblock" id="navh"><img src="logo.png" id="logo"/> Rippler</a></div></div><div class="col-xs-4 col-sm-4 col-md-3 col-lg-2"><div class="navblock"><div class="navtext" id="navw">Write</div></div></div><div class="col-xs-4 col-sm-4 col-md-3 col-lg-offset-4 col-lg-2"><div class="navblock"><div class="navtext" id="nave">Edit</div></div></div><div class="col-xs-4 col-sm-4 col-md-3 col-lg-2"><div class="navblock"><div class="navtext" id="navs">Advanced Search</div></div></div>'
				);
				$('#navh').click(function(){window.location = "/rippler";}); 
				$('#navw').click(function(){window.location = "/write";}); 
				$('#nave').click(function(){window.location = "/manage";}); 
				$('#navs').click(function(){window.location = "/search";}); 
			});
		})();
