# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_razorpay_public_token(self):
        super()._get_razorpay_public_token()
        return self.provider_id.razorpay_public_token
