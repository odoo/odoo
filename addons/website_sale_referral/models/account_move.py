# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_invoice_paid(self):
        # OVERRIDE
        for invoice in self:
            sos = self.env['sale.order'].search([('invoice_ids', '=', invoice.id)])
            for so in sos:
                if not so.deserve_reward and so.is_fully_paid():
                    new_state = so._get_referral_statuses(so.source_id, so.partner_id.email)
                    so._check_referral_progress('in_progress', new_state)
