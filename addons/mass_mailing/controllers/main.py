
from openerp import http
from openerp.http import request

class MassMailController(http.Controller):
    @http.route('/mail/track/<int:mail_id>/blank.gif', type='http', auth='admin')
    def track_mail_open(self, mail_id):
        """ Email tracking. """
        mail_mail_stats = request.registry.get('mail.mail.statistics')
        mail_mail_stats.set_opened(request.cr, request.uid, mail_mail_ids=[mail_id])
        return "data:image/gif;base64,R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
