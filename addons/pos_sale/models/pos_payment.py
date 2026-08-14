# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    def _check_online_account_payment_consistency(self, payment_method_id, online_account_payment_ids):
        """Bypass payment method/account payment consistency checks for sale order payment methods"""
        if not self.env['pos.payment.method'].browse(payment_method_id).exists().use_sale_order_payment:
            super()._check_online_account_payment_consistency(payment_method_id, online_account_payment_ids)
