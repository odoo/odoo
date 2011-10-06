import werkzeug.wrappers
import web.common.http as openerpweb
import web.controllers.main as web
import json
import textwrap

        

edi_import_template = textwrap.dedent("""<!DOCTYPE html>
<html style="height: 100%%">
    <head>
        <meta http-equiv="content-type" content="text/html; charset=utf-8" />
        <title>OpenERP</title>
        <link rel="shortcut icon" href="/web/static/src/img/favicon.ico" type="image/x-icon"/>
        
        %(css)s
        %(javascript)s
        <script type="text/javascript" src="/web_edi/static/src/js/edi_import.js"></script>
        <script type="text/javascript">
            $(function() {
                 var c = new openerp.init();

                 openerp.web.edi_import(c)
                
                 var import_engine = new c.web.EdiImport("oe");
                 import_engine.import_edi('%(edi_url)s');


            });
        </script>
    </head>
    <body id="oe" class="openerp"></body>
</html>
""")


class EDIImport(web.WebClient):
    #http://localhost:8002/web/import_edi?edi_url=XXXXX 
    # Note: edi_url should have url which passed from encodeURIComponent function
    _cp_path = "/web/import_edi"


    @openerpweb.httprequest
    def index(self, req, edi_url):
        # script tags
        addons = ['web']
        jslist = ['/web/webclient/js']
        if req.debug:
            jslist = [i + '?debug=' + str(time.time()) for i in web.manifest_glob(req.config.addons_path, addons, 'js')]
        js = "\n        ".join(['<script type="text/javascript" src="%s"></script>'%i for i in jslist])

        # css tags
        csslist = ['/web/webclient/css']
        if req.debug:
            csslist = [i + '?debug=' + str(time.time()) for i in web.manifest_glob(req.config.addons_path, addons, 'css')]
        css = "\n        ".join(['<link rel="stylesheet" href="%s">'%i for i in csslist])

        r = edi_import_template % {
            'javascript': js,
            'css': css,
            'edi_url': edi_url,
        }
        return r

    @openerpweb.jsonrequest
    def import_edi_url(self, req, edi_url):
        # call EDI Service: import_edi_url
        result = req.session.proxy('edi').import_edi_url(req.session._db, req.session._uid, req.session._password, edi_url)
        
        return result
    
