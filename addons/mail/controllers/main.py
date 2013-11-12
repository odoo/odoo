import base64
import psycopg2

import openerp
from openerp import SUPERUSER_ID
from openerp import http
from openerp.addons.web.controllers.main import content_disposition


class MailController(http.Controller):
    _cp_path = '/mail'

    @http.route('/mail/download_attachment', type='http', auth='user')
    def download_attachment(self, req, model, id, method, attachment_id, **kw):
        # FIXME use /web/binary/saveas directly
        Model = req.session.model(model)
        res = getattr(Model, method)(int(id), int(attachment_id))
        if res:
            filecontent = base64.b64decode(res.get('base64'))
            filename = res.get('filename')
            if filecontent and filename:
                return req.make_response(filecontent,
                    headers=[('Content-Type', 'application/octet-stream'),
                            ('Content-Disposition', content_disposition(filename))])
        return req.not_found()

    @http.route('/mail/receive', type='json', auth='none')
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
