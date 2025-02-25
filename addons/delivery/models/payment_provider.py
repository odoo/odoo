# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

from odoo.addons.delivery import const
from odoo.addons.payment import utils as payment_utils


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    custom_mode = fields.Selection(selection_add=[('cash_on_delivery', 'Cash On Delivery')])

    @api.model
    def _get_compatible_providers(self, *args, sale_order_id=None, report=None, **kwargs):
        """ Override of payment to exclude COD providers if the delivery method doesn't match.

        :param int sale_order_id: The sales order to be paid, if any, as a `sale.order` id.
        :param dict report: The availability report.
        :return: The compatible providers.
        :rtype: payment.provider
        """
        compatible_providers = super()._get_compatible_providers(
            *args, sale_order_id=sale_order_id, report=report, **kwargs
        )

        sale_order = self.env['sale.order'].browse(sale_order_id).exists()
        if not sale_order.carrier_id.allow_cash_on_delivery:
            unfiltered_providers = compatible_providers
            compatible_providers = compatible_providers.filtered(
                lambda p: p.custom_mode != 'cash_on_delivery'
            )
            payment_utils.add_to_report(
                report,
                unfiltered_providers - compatible_providers,
                available=False,
                reason=_("cash on delivery not allowed by selected delivery method"),
            )

        return compatible_providers

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.custom_mode != 'cash_on_delivery':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
