# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def set_no_tip(self):
        """Capture the payment when no tip is set."""
        res = super(PosOrder, self).set_no_tip()

        for payment in self.payment_ids:
            if payment.payment_method_id.use_payment_terminal == 'stripe':
                payment.payment_method_id.stripe_capture_payment(payment.transaction_id)

        return res
