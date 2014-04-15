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

    def get_recipients_data(self, cr, uid, mailing, res_ids, context=None):
        if mailing.mailing_model == 'crm.lead':
            res = {}
            for lead in self.pool['crm.lead'].browse(cr, uid, res_ids, context=context):
                if lead.partner_id:
                    res[lead.id] = {'partner_id': lead.partner_id.id, 'name': lead.partner_id.name, 'email': lead.partner_id.email}
                else:
                    name, email = self.pool['res.partner']._parse_partner_name(lead.email_from, context=context)
                    res[lead.id] = {'partner_id': False, 'name': name or email, 'email': email}
            return res
        return super(MassMailing, self).get_recipients_data(cr, uid, mailing, res_ids, context=context)
