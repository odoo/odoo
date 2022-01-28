# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pos_payment_method_id = fields.Many2one('pos.payment.method', "POS Payment Method")
    force_outstanding_account_id = fields.Many2one("account.account", "Forced Outstanding Account", check_company=True)
    pos_session_id = fields.Many2one('pos.session', "POS Session")

    def _get_outstanding_account_id(self):
        """When force_outstanding_account_id is set, we use it as the outstanding_account_id."""
        self.ensure_one()
        if self.force_outstanding_account_id:
            return self.force_outstanding_account_id
        else:
            return super()._get_outstanding_account_id()
