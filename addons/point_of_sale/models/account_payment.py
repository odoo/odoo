# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pos_payment_method_id = fields.Many2one('pos.payment.method', "POS Payment Method")
    force_outstanding_account_id = fields.Many2one("account.account", "Forced Outstanding Account", check_company=True)
    pos_session_id = fields.Many2one('pos.session', "POS Session")

    def _get_valid_liquidity_accounts(self):
        result = super()._get_valid_liquidity_accounts()
        return result | self.pos_payment_method_id.outstanding_account_id

    @api.depends("force_outstanding_account_id")
    def _compute_outstanding_account_id(self):
        """When force_outstanding_account_id is set, we use it as the outstanding_account_id."""
        super()._compute_outstanding_account_id()
        for payment in self:
            if payment.force_outstanding_account_id:
                payment.outstanding_account_id = payment.force_outstanding_account_id
