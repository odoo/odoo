import werkzeug.wrappers
import web.common.http as openerpweb
import web.controllers.main as web
import json
import textwrap

edi_view_template = textwrap.dedent("""<!DOCTYPE html>
<html style="height: 100%%">
    <head>
        <meta http-equiv="content-type" content="text/html; charset=utf-8" />
        <title>OpenERP</title>
        <link rel="shortcut icon" href="/web/static/src/img/favicon.ico" type="image/x-icon"/>
        %(css)s
        %(javascript)s
        <script type="text/javascript">
            $(function() {
                var c = new openerp.init();

                var files = eval(%(edi_js)s);
                for(var i=0; i<files.length; i++) {
                    if(openerp.web[files[i]]) {
                        openerp.web[files[i]](c);
                    }
                }
                var edi_engine = new c.web.EdiView("oe");
         	    edi_engine.view_edi('%(token)s', '%(db)s');

            });
        </script>
    </head>
    <body id="oe" class="openerp"></body>
</html>
""")

def edi_addons():
     #FIXME: hardcoded to be able to test 
    return 'web,edi,sale,purchase'

    _addons = ['web', 'edi', 'sale', 'purchase']
    for addon in openerpweb.addons_module:
        if addon in _addons:
            continue
        manifest = openerpweb.addons_manifest.get(addon, {})
        edi_addon = manifest.get('edi', False)
        if edi_addon:
            _addons.append(addon)
    return _addons

class EDIView(web.WebClient):
    #  http://path.to.web.client:8080/web/view_edi?db=XXX&token=XXXXXXXXXXX 
    _cp_path = "/web/view_edi"

    @openerpweb.httprequest
    def css(self, req):
        files = self.manifest_glob(req, edi_addons(), 'css')
        content,timestamp = web.concat_files(req.config.addons_path[0], files)
        # TODO request set the Date of last modif and Etag
        return req.make_response(content, [('Content-Type', 'text/css')])

    @openerpweb.httprequest
    def js(self, req):
        files = self.manifest_glob(req, edi_addons(), 'js')
        content,timestamp = web.concat_files(req.config.addons_path[0], files)
        # TODO request set the Date of last modif and Etag
        return req.make_response(content, [('Content-Type', 'application/javascript')])
    
    @openerpweb.httprequest
    def index(self, req, token, db):
        # script tags
        addons = edi_addons()
        jslist = ['/web/view_edi/js']
        if req.debug:
            jslist = [i + '?debug=' + str(time.time()) for i in self.manifest_glob(req, addons, 'js')]
        js = "\n        ".join(['<script type="text/javascript" src="%s"></script>'%i for i in jslist])

        # css tags
        csslist = ['/web/view_edi/css']
        if req.debug:
            csslist = [i + '?debug=' + str(time.time()) for i in self.manifest_glob(req, addons, 'css')]
        css = "\n        ".join(['<link rel="stylesheet" href="%s">'%i for i in csslist])

        js_files = [str(js_file.split('/')[-1].split('.')[0]) for js_file in self.manifest_glob(req, addons, 'js')]
            
        r = edi_view_template % {
            'javascript': js,
            'css': css,
            'token': token,
            'db': db,
            'edi_js': js_files
        }
        return r
        


