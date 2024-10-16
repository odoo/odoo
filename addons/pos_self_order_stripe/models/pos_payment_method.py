from odoo import models
from odoo.addons import pos_self_order, pos_stripe


class PosPaymentMethod(pos_stripe.PosPaymentMethod, pos_self_order.PosPaymentMethod):

    def _payment_request_from_kiosk(self, order):
        if self.use_payment_terminal != 'stripe':
            return super()._payment_request_from_kiosk(order)
        else:
            return self.stripe_payment_intent(order.amount_total)
