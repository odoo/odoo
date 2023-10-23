from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def payment_request_from_kiosk(self, order):
        if self.use_payment_terminal != 'stripe':
            return super().payment_request_from_kiosk(order)
        else:
            return self.stripe_payment_intent(order.amount_total)
