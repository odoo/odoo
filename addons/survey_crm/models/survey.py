# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SurveyComposeMessage(models.TransientModel):

    _inherit = 'survey.mail.compose.message'

    @api.model
    def default_get(self, fields):
        result = super(SurveyComposeMessage, self).default_get(fields)
        if self._context.get('active_model') == 'crm.lead' and self._context.get('active_ids'):
            partner_ids = []
            emails_list = []
            for lead in self.env['crm.lead'].browse(self._context.get('active_ids')):
                if lead.partner_id:
                    partner_ids.append(lead.partner_id.id)
                else:
                    email = lead.contact_name and "%s <%s>" % (lead.contact_name, lead.email_from or "") or lead.email_from or None
                    if email and email not in emails_list:
                        emails_list.append(email)
            multi_email = "\n".join(emails_list)

            result.update({'partner_ids': list(set(partner_ids)), 'multi_email': multi_email})
        return result
