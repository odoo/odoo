import base64
import openerp.addons.web.http as oeweb
from openerp.addons.web.controllers.main import content_disposition

#----------------------------------------------------------
# Controller
#----------------------------------------------------------
class MailController(oeweb.Controller):
    _cp_path = '/mail'

    @oeweb.httprequest
    def download_attachment(self, req, model, id, method, attachment_id, **kw):
        Model = req.session.model(model)
        res = getattr(Model, method)(int(id), int(attachment_id))
        if res:
            filecontent = base64.b64decode(res.get('base64'))
            filename = res.get('filename')
            if filecontent and filename:
                return req.make_response(filecontent,
                    headers=[('Content-Type', 'application/octet-stream'),
                            ('Content-Disposition', content_disposition(filename, req))])
        return req.not_found()
