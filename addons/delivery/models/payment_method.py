# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    @api.model
    def _get_payment_method_on_delivery_codes(self):
        """Return the technical codes of "Pay on Delivery" payment methods."""
        return ['cash_on_delivery']
