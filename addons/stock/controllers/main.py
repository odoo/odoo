# -*- coding: utf-8 -*-
import logging
import simplejson
import os
import openerp
import time
import random

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import manifest_list, module_boot, html_template

_logger = logging.getLogger(__name__)

html_template = """<!DOCTYPE html>
<html>
    <head>
        <title>Barcode Scanner</title>

        <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1"/>
        <meta http-equiv="content-type" content="text/html, charset=utf-8" />

        <meta name="viewport" content=" width=1024, user-scalable=no">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="mobile-web-app-capable" content="yes">

        <link rel="shortcut icon"    sizes="80x51" href="/stock/static/src/img/scan.png">
        <link rel="shortcut icon" href="/web/static/src/img/favicon.ico" type="image/x-icon"/>
        <link rel="stylesheet" href="/stock/static/src/css/barcode.css" />
        <link rel="stylesheet" href="/web/static/lib/bootstrap/css/bootstrap.css" /> 
        <link rel="stylesheet" href="/web/static/lib/jquery.ui/css/smoothness/jquery-ui-1.9.1.custom.css" />
        <link rel="stylesheet" href="/web/static/lib/fontawesome/css/font-awesome.css" />
        <script type="text/javascript" src="/web/js/web.assets_backend"></script>
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

class BarcodeController(http.Controller):

    @http.route(['/barcode/web/'], type='http', auth='user')
    def a(self, debug=False, **k):
        if not request.session.uid:
            return http.local_redirect('/web/login?redirect=/barcode/web')

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
                         wc.action_manager.do_action("stock.ui", {});
                     };
                     wc.do_push_state = function(state){};
                     wc.appendTo($(document.body));
                     """
        }
        return r
