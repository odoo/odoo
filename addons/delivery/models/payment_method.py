# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    @api.model
    def _get_payment_method_at_delivery_codes(self):
        """Return the technical codes of payment methods whose transactions should be
        marked as done when the order is delivered."""
        return ['cash_on_delivery']
