# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_invoice_paid(self):
        sos = self.env['sale.order'].search([('invoice_ids', 'in', self.ids)])
        for so in sos.filtered(lambda so: not so.deserve_reward and so._is_fully_paid()):
            new_state = so._get_referral_statuses(so.source_id, so.partner_id.email)
            so._check_and_apply_progress('in_progress', new_state)
        return super().action_invoice_paid()
