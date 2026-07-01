# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentMethod(models.Model):
    _inherit = "payment.method"

    def _is_postpaid(self):
        """Override of `payment` to mark Pay on Site as postpaid."""
        if self.code != "pay_on_site":
            return super()._is_postpaid()

        return True

    @api.model
    def _get_payment_method_on_delivery_codes(self):
        return super()._get_payment_method_on_delivery_codes() + ["pay_on_site"]
