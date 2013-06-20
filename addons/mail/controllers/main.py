import base64

import openerp
from openerp import SUPERUSER_ID
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

    @oeweb.jsonrequest
    def receive(self, req):
        """ End-point to receive mail from an external SMTP server. """
        dbs = req.jsonrequest.get('databases')
        for db in dbs:
            message = dbs[db].decode('base64')
            try:
                registry = openerp.registry(db)
                with registry.cursor() as cr:
                    mail_thread = registry['mail.thread']
                    mail_thread.message_process(cr, SUPERUSER_ID, None, message)
            except psycopg2.Error:
                pass
        return True
