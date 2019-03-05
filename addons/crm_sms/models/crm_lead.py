# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def _get_default_sms_recipients(self):
        """ Override of mail.thread method.
        """
        return self.mapped('partner_id')

    def action_send_sms(self):
        sendto = []
        recipients = []
        # creating a new context based on the default because of 'crm_send_sms_action' which has a different context
        # than the buttons 'Send SMS Text Message'
        context = dict(self.env.context)

        no_phones = []

        for lead in self:
            number = lead[self.env.context.get('field_name')] if self.env.context.get('field_name') else lead['partner_address_phone'] or lead['mobile'] or lead['phone']
            partner = lead._get_default_sms_recipients()

            if number:
                recipients.append(number)
                sendto.append('%s - %s' % (partner.name, number) if partner else number)
            else:
                no_phones.append(lead.name)

        if no_phones:
            raise UserError('No phone number found for lead(s): %s' % ', '.join(no_phones))

        context['default_sendto'] = '\n'.join(sorted(sendto))
        context['default_recipients'] = ', '.join(recipients)

        return {
            "type": "ir.actions.act_window",
            "res_model": "sms.send_sms",
            "context": context,
            "view_mode": 'form',
            "name": "Send SMS",
            "target": "new",
        }
