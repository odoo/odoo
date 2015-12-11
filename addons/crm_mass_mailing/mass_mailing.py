from openerp.osv import osv


class MassMailing(osv.Model):
    _name = 'mail.mass_mailing'
    _inherit = ['mail.mass_mailing', 'crm.tracking.mixin']

    def on_change_model_and_list(self, cr, uid, ids, mailing_model, list_ids, context=None):
        res = super(MassMailing, self).on_change_model_and_list(cr, uid, ids, mailing_model, list_ids, context=context)
        if mailing_model == 'crm.lead':
            res = res or {}
            values = {'mailing_domain': "[('opt_out', '=', False)]"}
            res = dict(res, value=dict(res.get('value', {}), **values))
        return res
