# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    def _can_return_content(self, field_name=None, access_token=None):
        # The `image` field is fetched by public users through `/web/image` URL
        # in `s_supported_payment_methods` snippet
        if field_name == 'image':
            return True
        return super()._can_return_content(field_name, access_token)
