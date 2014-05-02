
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request


class MassMailController(http.Controller):

    @http.route('/mail/track/<int:mail_id>/blank.gif', type='http', auth='none')
    def track_mail_open(self, mail_id, **post):
        """ Email tracking. """
        mail_mail_stats = request.registry.get('mail.mail.statistics')
        mail_mail_stats.set_opened(request.cr, SUPERUSER_ID, mail_mail_ids=[mail_id])
        response = werkzeug.wrappers.Response()
        response.mimetype = 'image/gif'
        response.data = 'R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=='.decode('base64')
        return response

    @http.route(['/mail/mailing/<int:mailing_id>/unsubscribe'], type='http', auth='none')
    def mailing(self, mailing_id, email=None, res_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        MassMailing = request.registry['mail.mass_mailing']
        mailing_ids = MassMailing.exists(cr, SUPERUSER_ID, [mailing_id], context=context)
        if not mailing_ids:
            return 'KO'
        mailing = MassMailing.browse(cr, SUPERUSER_ID, mailing_ids[0], context=context)
        if mailing.mailing_model == 'mail.mass_mailing.contact':
            list_ids = [l.id for l in mailing.contact_list_ids]
            record_ids = request.registry[mailing.mailing_model].search(cr, SUPERUSER_ID, [('list_id', 'in', list_ids), ('id', '=', res_id), ('email', 'ilike', email)], context=context)
            request.registry[mailing.mailing_model].write(cr, SUPERUSER_ID, record_ids, {'opt_out': True}, context=context)
        else:
            email_fname = None
            if 'email_from' in request.registry[mailing.mailing_model]._all_columns:
                email_fname = 'email_from'
            elif 'email' in request.registry[mailing.mailing_model]._all_columns:
                email_fname = 'email'
            if email_fname:
                record_ids = request.registry[mailing.mailing_model].search(cr, SUPERUSER_ID, [('id', '=', res_id), (email_fname, 'ilike', email)], context=context)
            if 'opt_out' in request.registry[mailing.mailing_model]._all_columns:
                request.registry[mailing.mailing_model].write(cr, SUPERUSER_ID, record_ids, {'opt_out': True}, context=context)
        return 'OK'
