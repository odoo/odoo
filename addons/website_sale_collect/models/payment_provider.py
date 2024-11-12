# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.addons.payment import utils as payment_utils
from odoo.addons.website_sale_collect import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    custom_mode = fields.Selection(
        selection_add=[('on_site', "Pay on site")]
    )

    @api.model
    def _get_compatible_providers(
        self, company_id, *args, sale_order_id=None, website_id=None, report=None, **kwargs
    ):
        """ Override of payment to exclude on-site payment providers if the delivery method is not
        pick up in store.

        :param int company_id: The company to which providers must belong, as a `res.company` id
        :param int sale_order_id: The sale order to be paid, if any, as a `sale.order` id
        :param int website_id: The provided website, as a `website` id
        :param dict report: The availability report.
        :return: The compatible providers
        :rtype: recordset of `payment.provider`
        """
        compatible_providers = super()._get_compatible_providers(
            company_id,
            *args,
            sale_order_id=sale_order_id,
            website_id=website_id,
            report=report,
            **kwargs,
        )
        order = self.env['sale.order'].browse(sale_order_id).exists()

        # Show on-site payment providers only if in-store delivery methods exist and the order
        # contains physical products.
        if order.carrier_id.delivery_type != 'in_store' or not any(
            product.type == 'consu'
            for product in order.order_line.product_id
        ):
            unfiltered_providers = compatible_providers
            compatible_providers = compatible_providers.filtered(
                lambda p: p.code != 'custom' or p.custom_mode != 'on_site'
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - compatible_providers,
                available=False,
                reason=_("no in-store delivery methods available"),
            )

        return compatible_providers

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.custom_mode != 'on_site':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
