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
        ids = []
        sendto = '...'
        recipients = ''

        print('??')

        for record in self:
            # if no mobile or phone number then error
            pass

        return {
            "type": "ir.actions.act_window",
            "res_model": "sms.send_sms",
            "view_mode": 'form',
            "context": {
                'active_ids': ids,
                'default_recipients': recipients,
                'default_sendto': sendto
            },
            "name": "Send SMS",
            "target": "new",
        }
