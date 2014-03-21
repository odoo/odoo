
from openerp import http, SUPERUSER_ID
from openerp.http import request


class MassMailController(http.Controller):

    @http.route('/mail/track/<int:mail_id>/blank.gif', type='http', auth='none')
    def track_mail_open(self, mail_id):
        print 'tracking', mail_id
        """ Email tracking. """
        mail_mail_stats = request.registry.get('mail.mail.statistics')
        mail_mail_stats.set_opened(request.cr, SUPERUSER_ID, mail_mail_ids=[mail_id])
        return "data:image/gif;base64,R0lGODlhAQABAIAAANvf7wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="

    @http.route(['/mail/mailing/<int:mailing_id>/unsubscribe'], type='http', auth='none')
    def mailing(self, mailing_id, email=None, model=None, res_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        print 'unsubscribing from', mailing_id, email, model, res_id
        MassMailing = request.registry['mail.mass_mailing']
        # check model is valid
        # ...
        mailing_ids = MassMailing.exists(cr, SUPERUSER_ID, [mailing_id], context=context)
        if not mailing_ids:
            print 'wrroooooong'
            return ''
        if model == 'res.partner':
            partner_ids = request.registry[model].search(cr, SUPERUSER_ID, [('id', '=', res_id), ('email', 'ilike', email)], context=context)
            print 'Setting partner_ids', partner_ids, 'as opt out'
            # request.registry[model].write(cr, SUPERUSER_ID, partner_ids, {'opt_out': True}, context=context)
        else:
            mailing = MassMailing.browse(cr, SUPERUSER_ID, mailing_ids[0], context=context)
            list_ids = [l.id for l in mailing.contact_list_ids]
            res_ids = request.registry[model].search(cr, SUPERUSER_ID, [('list_id', 'in', list_ids), ('id', '=', res_id), ('email', 'ilike', email)], context=context)
            print 'Setting contacts', res_ids, 'as opt out'
            # request.registry[model].write(cr, SUPERUSER_ID, res_ids, {'opt_out': True}, context=context)
        return ''
