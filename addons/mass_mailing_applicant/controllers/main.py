
from openerp import http, SUPERUSER_ID
from openerp.addons.mass_mailing.controllers import main
from openerp.http import request


class MassMailController(main.MassMailController):

    @http.route(['/mail/mailing/<int:mailing_id>/unsubscribe'], type='http', auth='none')
    def mailing(self, mailing_id, email=None, res_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        MassMailing = request.registry['mail.mass_mailing']
        mailing_ids = MassMailing.exists(cr, SUPERUSER_ID, [mailing_id], context=context)
        if not mailing_ids:
            return super(MassMailController, self).mailing(mailing_id, email=email, res_id=res_id, **post)
        mailing = MassMailing.browse(cr, SUPERUSER_ID, mailing_ids[0], context=context)
        if mailing.mailing_model == 'hr.applicant':
            record_ids = request.registry[mailing.mailing_model].search(cr, SUPERUSER_ID, [('id', '=', res_id), ('email_from', 'ilike', email)], context=context)
            # request.registry[mailing.mailing_model].write(cr, SUPERUSER_ID, record_ids, {'opt_out': True}, context=context)
            return 'OK'
        return super(MassMailController, self).mailing(mailing_id, email=email, res_id=res_id, **post)
