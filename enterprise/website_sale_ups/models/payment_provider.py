# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.addons.website_sale_ups import const
from odoo.addons.payment import utils as payment_utils


class Paymentprovider(models.Model):
    _inherit = 'payment.provider'

    custom_mode = fields.Selection(
        selection_add=[('cash_on_delivery', 'Cash On Delivery')]
    )

    @api.model
    def _get_compatible_providers(
        self, *args, sale_order_id=None, website_id=None, report=None, **kwargs
    ):
        """ Override of payment to exclude COD providers if the delivery doesn't match.

        :param int sale_order_id: The sale order to be paid, if any, as a `sale.order` id
        :param int website_id: The website on which the order is placed, if any, as a `website` id.
        :param dict report: The availability report.
        :return: The compatible providers
        :rtype: recordset of `payment.provider`
        """
        compatible_providers = super()._get_compatible_providers(
            *args, sale_order_id=sale_order_id, website_id=website_id, report=report, **kwargs
        )

        sale_order = self.env['sale.order'].browse(sale_order_id).exists()
        if sale_order.carrier_id.delivery_type != 'ups' or not any(
            product.type == 'consu'
            for product in sale_order.order_line.product_id
        ):
            unfiltered_providers = compatible_providers
            compatible_providers = compatible_providers.filtered(
                lambda p: p.code != 'custom' or p.custom_mode != 'cash_on_delivery'
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - compatible_providers,
                available=False,
                reason=_("no UPS carriers available"),
            )

        return compatible_providers

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.custom_mode != 'cash_on_delivery':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
