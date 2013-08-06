import base64
import psycopg2

import openerp
from openerp import SUPERUSER_ID
import openerp.addons.web.http as http
from openerp.addons.web.controllers.main import content_disposition
from openerp.addons.web.http import request


class MailController(http.Controller):
    _cp_path = '/mail'

    @http.httprequest
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

    @http.jsonrequest
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

    @http.route('/mail/track/<int:mail_id>/blank.gif', type='http', auth='admin')
    def track_read_email(self, mail_id):
        """ Email tracking. """
        mail_mail = request.registry.get('mail.mail')
        mail_mail.set_opened(request.cr, request.uid, [mail_id])
        return False
