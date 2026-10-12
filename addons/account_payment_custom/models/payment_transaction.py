# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    # === LIFECYCLE METHODS - POST-PROCESSING === #

    def _should_create_payment(self):
        """Override of ``account_payment`` to avoid creating payments for Pay on Invoice."""
        return super()._should_create_payment() and self.payment_method_code != "pay_on_invoice"
