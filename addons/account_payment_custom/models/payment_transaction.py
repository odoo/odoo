# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    # === LIFECYCLE METHODS - POST-PROCESSING === #

    def _should_create_payment(self):
        """Override of `account_payment` to avoid creating payments for post-paid transactions."""
        return super()._should_create_payment() and not self.payment_method_id._is_postpaid()
