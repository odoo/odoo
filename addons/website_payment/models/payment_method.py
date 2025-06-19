# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    def _get_available_payment_methods(self, limit=None):
        """Retrieve the published payment methods brands to be displayed using the
        `s_supported_payment_methods` snippet.

        :param int limit: Limit the number of payment method returned.
        :rtype: list[{ 'id': int, 'name': str, 'code': str }]
        :return: The payment methods either because they are the brand of a primary payment
            method or because the brand is a primary payment method.
        """
        # Sudoed to be able to read the brands of primary methods
        return self.env['payment.method'].sudo().search_read(
            [
                '|', '&', ('is_primary', '=', True),
                     '&', ('provider_ids.is_published', '=', True),
                          ('brand_ids', '=', False),
                     '&', ('is_primary', '=', False),
                          ('primary_payment_method_id.provider_ids.is_published', '=', True),
            ],
            fields=('id', 'name', 'code'),
            limit=limit,
            order='sequence',
        )
