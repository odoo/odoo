# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosPayment(models.Model):
    _inherit = "pos.payment"

    def _update_payment_line_for_tip(self, tip_amount):
        """Capture the payment when a tip is set."""
        res = super()._update_payment_line_for_tip(tip_amount)

        if self.payment_method_id.use_payment_terminal == "stripe":
            self.payment_method_id.stripe_capture_payment(
                self.transaction_id,
                amount=self.amount,
            )

        return res
