# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentMethod(models.Model):
    _inherit = "payment.method"

    @api.model
    def _get_pay_on_delivery_method_codes(self):
        return super()._get_pay_on_delivery_method_codes() | {"pay_on_site"}
