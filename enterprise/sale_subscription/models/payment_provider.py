# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import REPORT_REASONS_MAPPING


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
            if (sale_order.is_subscription or sale_order.subscription_id.is_subscription) and \
                    not kwargs.get('show_non_tokenize_provider'):
                return True
        return super()._is_tokenization_required(sale_order_id=sale_order_id, **kwargs)

    @api.model
    def _get_compatible_providers(
        self, *args, sale_order_id=None, website_id=None, report=None, **kwargs
    ):
        """ Override of payment to exclude manually captured providers.

        :param int sale_order_id: The sale order to be paid, if any, as a `sale.order` id
        :param int website_id: The website on which the order is placed, if any, as a `website` id.
        :param dict report: The availability report.
        :return: The compatible providers
        :rtype: recordset of `payment.provider`
        """
        compatible_providers = super()._get_compatible_providers(
            *args, sale_order_id=sale_order_id, website_id=website_id, report=report, show_non_tokenize_provider=True, **kwargs
        )
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id).exists()
            if sale_order.is_subscription or sale_order.subscription_id.is_subscription:
                manual_capture_providers = compatible_providers.filtered("capture_manually")
                compatible_providers -= manual_capture_providers
                payment_utils.add_to_report(
                    report,
                    manual_capture_providers,
                    available=False,
                    reason=REPORT_REASONS_MAPPING['manual_capture_not_supported'],
                )

                exceed_max_amount_providers = compatible_providers.filtered(
                    lambda provider: provider.maximum_amount > 0
                    and provider.main_currency_id.compare_amounts(sale_order.amount_total, provider.maximum_amount) == 1
                )
                compatible_providers -= exceed_max_amount_providers
                payment_utils.add_to_report(
                    report,
                    exceed_max_amount_providers,
                    available=False,
                    reason=REPORT_REASONS_MAPPING['exceed_max_amount'],
                )

        return compatible_providers
