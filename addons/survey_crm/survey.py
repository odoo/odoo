# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv


class survey_mail_compose_message(osv.TransientModel):
    _inherit = 'survey.mail.compose.message'

    def default_get(self, cr, uid, fields, context=None):
        res = super(survey_mail_compose_message, self).default_get(cr, uid, fields, context=context)
        if context.get('active_model') == 'crm.lead' and context.get('active_ids'):
            partner_ids = []
            emails_list = []
            for lead in self.pool.get('crm.lead').browse(cr, uid, context.get('active_ids'), context=context):
                if lead.partner_id:
                    partner_ids.append(lead.partner_id.id)
                else:
                    email = lead.contact_name and "%s <%s>" % (lead.contact_name, lead.email_from or "") or lead.email_from or None
                    if email and email not in emails_list:
                        emails_list.append(email)
            multi_email = "\n".join(emails_list)

            res.update({'partner_ids': list(set(partner_ids)), 'multi_email': multi_email})
        return res
