# -*- coding: utf-8 -*-

from openerp.osv import osv


class MassMailing(osv.Model):
    """Inherit to add crm.lead objects available for mass mailing """
    _name = 'mail.mass_mailing'
    _inherit = 'mail.mass_mailing'

    def _get_mailing_model(self, cr, uid, context=None):
        res = super(MassMailing, self)._get_mailing_model(cr, uid, context=context)
        res.append(('crm.lead', 'Leads / Opportunities'))
        return res

    def _get_model_to_list_action_id(self, cr, uid, model, context=None):
        if model == 'crm.lead':
            return self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'mass_mailing.action_lead_to_mailing_list')
        else:
            return super(MassMailing, self)._get_model_to_list_action_id(cr, uid, model, context=context)

    def _get_mail_recipients(self, cr, uid, mailing, res_ids, context=None):
        if mailing.mailing_model == 'crm.lead':
            res = {}
            for lead in self.pool['crm.lead'].browse(cr, uid, res_ids, context=context):
                if lead.partner_id:
                    res[lead.id] = {'recipient_ids': [(4, lead.partner_id.id)]}
                else:
                    res[lead.id] = {'email_to': [(4, lead.email_from)]}
            return res
        return super(MassMailing, self)._get_mail_recipients(cr, uid, mailing, res_ids, context=context)
