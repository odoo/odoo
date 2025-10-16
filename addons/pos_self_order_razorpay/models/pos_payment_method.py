import uuid
from odoo import models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _payment_request_from_kiosk(self, order):
        if self.payment_provider != 'razorpay':
            return super()._payment_request_from_kiosk(order)
        reference_prefix = order.config_id.name.replace(' ', '')
        data = {
            'amount': order.amount_total,
            'referenceId': f'{reference_prefix}/Order/{order.id}/{uuid.uuid4().hex}',
        }
        return self.razorpay_make_payment_request(data)
