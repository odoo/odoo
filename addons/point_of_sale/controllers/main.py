# -*- coding: utf-8 -*-
import logging
import simplejson
import os
import openerp
import time
import random

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import manifest_list, module_boot, html_template, login_redirect

_logger = logging.getLogger(__name__)

html_template = """<!DOCTYPE html>
<html>
    <head>
        <title>OpenERP POS</title>

        <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"/>
        <meta http-equiv="content-type" content="text/html, charset=utf-8" />

        <meta name="viewport" content=" width=1024, user-scalable=no">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="mobile-web-app-capable" content="yes">

        <link rel="shortcut icon"    sizes="196x196" href="/point_of_sale/static/src/img/touch-icon-196.png">
        <link rel="shortcut icon"    sizes="128x128" href="/point_of_sale/static/src/img/touch-icon-128.png">
        <link rel="apple-touch-icon"                 href="/point_of_sale/static/src/img/touch-icon-iphone.png">
        <link rel="apple-touch-icon" sizes="76x76"   href="/point_of_sale/static/src/img/touch-icon-ipad.png">
        <link rel="apple-touch-icon" sizes="120x120" href="/point_of_sale/static/src/img/touch-icon-iphone-retina.png">
        <link rel="apple-touch-icon" sizes="152x152" href="/point_of_sale/static/src/img/touch-icon-ipad-retina.png">

        <link rel="shortcut icon" href="/web/static/src/img/favicon.ico" type="image/x-icon"/>
        <link rel="stylesheet" href="/point_of_sale/static/src/fonts/lato/stylesheet.css" /> 
        <link rel="stylesheet" href="/point_of_sale/static/src/fonts/font-awesome-4.0.3/css/font-awesome.min.css" /> 
        <link rel="stylesheet" href="/point_of_sale/static/src/css/pos.css" />
        <link rel="stylesheet" href="/point_of_sale/static/src/css/keyboard.css" />
        %(js)s
        <script type="text/javascript">
            $(function() {
                var s = new openerp.init(%(modules)s);
                %(init)s
            });
        </script>
    </head>
    <body>
        <!--[if lte IE 8]>
        <script src="//ajax.googleapis.com/ajax/libs/chrome-frame/1/CFInstall.min.js"></script>
        <script>CFInstall.check({mode: "overlay"});</script>
        <![endif]-->
    </body>
</html>
"""

class PosController(http.Controller):

    @http.route('/pos/web', type='http', auth='none')
    def a(self, debug=False, **k):

        if not request.session.uid:
            return login_redirect()

        js_list = manifest_list('js',db=request.db, debug=debug)
        css_list =   manifest_list('css',db=request.db, debug=debug)
        
        js = "\n".join('<script type="text/javascript" src="%s"></script>' % i for i in js_list)
        #css = "\n".join('<link rel="stylesheet" href="%s">' % i for i in css_list)
        r = html_template % {
            'js': js,
         #   'css': css,
            'modules': simplejson.dumps(module_boot(request.db)),
            'init': """
                     var wc = new s.web.WebClient();
                     wc.show_application = function(){
                         wc.action_manager.do_action("pos.ui");
                     };
                     wc.appendTo($(document.body));
                     """
        }
        return r
