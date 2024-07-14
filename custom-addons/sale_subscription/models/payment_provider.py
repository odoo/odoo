# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentProvider(models.Model):

    _inherit = 'payment.provider'

    @api.model
    def _is_tokenization_required(self, sale_order_id=None, **kwargs):
        """ Override of `payment` to force tokenization when paying for a subscription.

        :param int sale_order_id: The sales order to be paid, as a `sale.order` id.
        :return: Whether tokenization is required.
        :rtype: bool
        """
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id).exists()
            if sale_order.is_subscription or sale_order.subscription_id.is_subscription:
                return True
        return super()._is_tokenization_required(sale_order_id=sale_order_id, **kwargs)

    @api.model
    def _get_compatible_providers(self, *args, sale_order_id=None, website_id=None, **kwargs):
        """ Override of payment to exclude manually captured providers.

        :param int sale_order_id: The sale order to be paid, if any, as a `sale.order` id
        :param int website_id: The website on which the order is placed, if any, as a `website` id.
        :return: The compatible providers
        :rtype: recordset of `payment.provider`
        """
        compatible_providers = super()._get_compatible_providers(
            *args, sale_order_id=sale_order_id, website_id=website_id, **kwargs
        )
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id).exists()
            if sale_order.is_subscription or sale_order.subscription_id.is_subscription:
                return compatible_providers.filtered(
                    lambda provider: not provider.capture_manually
                )
        return compatible_providers
