#from base.controllers.main import View
import web.common as openerpweb
import json
import cherrypy

class EDIView(openerpweb.Controller):
    #  http://path.to.web.client:8080/edi/view_edi?db=XXX&token=XXXXXXXXXXX 
    _cp_path = "/edi/view_edi"
    
    @openerpweb.httprequest
    def index(self, req, token, db):
        js_list = []
        css_list = []
        for addon in openerpweb.addons_module:
            if addon in ['web_edi']:
                continue
            manifest = openerpweb.addons_manifest.get(addon, {})
            edi_addon = manifest.get('edi', False)
            
            if edi_addon:
                js_list += map(lambda x: '/'+addon+'/'+x, manifest.get('js', []))
                css_list += map(lambda x: '/'+addon+'/'+x, manifest.get('css', []))
        
        out = """
<!DOCTYPE html>
<html style="height: 100%">
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <title>OpenERP</title>
    <script type="text/javascript" src="/base/static/lib/underscore/underscore.js"></script>
    <script type="text/javascript" src="/base/static/lib/underscore/underscore.string.js"></script>
    <script type="text/javascript" src="/base/static/lib/jquery/jquery-1.5.2.js"></script>
    <script type="text/javascript" src="/base/static/lib/json/json2.js"></script>
    <script type="text/javascript" src="/base/static/lib/qweb/qweb2.js"></script>
    <script type="text/javascript" src="/base/static/src/js/base.js"></script>
    <script type="text/javascript" src="/base/static/src/js/chrome.js"></script>
    <script type="text/javascript" src="/web_edi/static/src/js/edi.js"></script>
    <link rel="stylesheet" href="/base/static/src/css/base.css" type="text/css"/>
    """
        for js in js_list:
            out += """<script type="text/javascript" src="%s"></script>""" %(js)
        for css in css_list:
            out += """<link rel="stylesheet" href="%s" type="text/css"/>""" %(css)
        out += """<script language="javascript" type="text/javascript">
            QWeb = window.QWeb || new QWeb2.Engine();
            var view_edi = new openerp.edi.EdiView("oe");
         	view_edi.view_edi('"""+token+"""', '"""+db+"""');
        </script>
    
    <body id="oe" class="openerp">
    </body>
</head>
</html>
                """
        return out

class EDIGet(openerpweb.Controller):
    # http://path.to.web.client:8080/edi/get_edi?db=XXXX&token=XXXXXXXXXXX
    _cp_path = "/edi/get_edi"

    @openerpweb.httprequest
    def index(self, req, token, db):
        response = req.session.proxy('edi').get_edi_document(token, db)
        cherrypy.response.headers['Content-Type'] = 'application/json'
        cherrypy.response.headers['Content-Length'] = len(response)
        return response

    @openerpweb.jsonrequest
    def get_edi_document(self, req, token, db):
        response = req.session.proxy('edi').get_edi_document(token, db)
        document = json.loads(response)
        model = document and document[0].get('__model')
        cherrypy.response.headers['Content-Type'] = 'application/json'
        cherrypy.response.headers['Content-Length'] = len(response)
        return {'token': token, 'db': db, 'model':model.replace('.','_'), 'document':response}
        
class EDIImport(openerpweb.Controller):
    #http://localhost:8002/base/static/src/base.html?import_edi&edi_url=XXXXX 
    # Note: edi_url should have url which passed from encodeURIComponent function
    _cp_path = "/edi/import_edi"

    @openerpweb.jsonrequest
    def index(self, req, edi_url):
        # call EDI Service: import_edi_url
        print 'EDI_IMPORT', req, edi_url
        res = req.session.proxy('edi').import_edi_url(req.session._db, req.session._uid, req.session._password, edi_url)
        return res
    
