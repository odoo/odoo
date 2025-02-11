# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.website_sale_picking import const

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    custom_mode = fields.Selection(
        selection_add=[('onsite', "On Site")]
    )

    @api.model
    def _get_compatible_providers(self, *args, sale_order_id=None, website_id=None, **kwargs):
        """ Override of payment to exclude onsite providers if the delivery doesn't match.

        :param int sale_order_id: The sale order to be paid, if any, as a `sale.order` id
        :param int website_id: The provided website, as a `website` id
        :return: The compatible providers
        :rtype: recordset of `payment.provider`
        """
        compatible_providers = super()._get_compatible_providers(
            *args, sale_order_id=sale_order_id, website_id=website_id, **kwargs)
        # Show on site picking only if delivery carriers onsite exists
        onsite_carriers = self.env['delivery.carrier'].search([
            ('website_published', '=', True),
            ('delivery_type', '=', 'onsite'),
            '|',
                ('website_id', '=?', website_id),
                ('website_id', '=', False)
        ])
        order = self.env['sale.order'].browse(sale_order_id).exists()

        # Show onsite providers only if onsite carriers exists
        # and the order contains physical products
        if not onsite_carriers or not any(
            product.type in ('consu', 'product')
            for product in order.order_line.product_id
        ):
            compatible_providers = compatible_providers.filtered(
                lambda p: p.code != 'custom' or p.custom_mode != 'onsite'
            )

        return compatible_providers

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.custom_mode != 'onsite':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
