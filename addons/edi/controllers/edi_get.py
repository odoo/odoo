import werkzeug.wrappers
import web.common.http as openerpweb
import json

class EDIGet(openerpweb.Controller):
    # http://path.to.web.client:8080/web/get_edi?db=XXXX&token=XXXXXXXXXXX
    _cp_path = "/web/get_edi"

    @openerpweb.httprequest
    def index(self, req, db, token):
        result = req.session.proxy('edi').get_edi_document(db, token)
        response = werkzeug.wrappers.Response(
                     result, headers=[('Content-Type', 'text/html; charset=utf-8'),
                                         ('Content-Length', len(result))])
                
        return response

    @openerpweb.jsonrequest
    def get_edi_document(self, req, db, token):
        result = req.session.proxy('edi').get_edi_document(db, token)
        document = json.loads(result)
        model = document and document[0].get('__model')
        return {'token': token, 'db': db, 'model':model.replace('.','_'), 'document':document}


