# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.website_sale.controllers.payment import PaymentPortal


class OnSitePaymentPortal(PaymentPortal):

    def _validate_transaction_for_order(self, transaction, sale_order):
        """ Override of `website_sale` to ensure the on-site payment provider is not used without
        the in-store pickup delivery method.

        This also sets the warehouse of the selected pickup location on the sales order.

        :param payment.transaction transaction: The transaction used to make the payment.
        :param sale.order sale_order: The sales order to pay.
        :return: None
        :raises ValidationError: If the user tries to pay on site without the in-store pickup
                                 delivery method.
        """
        super()._validate_transaction_for_order(transaction, sale_order)

        # This should never be triggered unless the user intentionally forges a request.
        provider = transaction.provider_id
        if (
            sale_order.carrier_id.delivery_type != 'in_store'
            and provider.code == 'custom'
            and provider.custom_mode == 'on_site'
        ):
            raise ValidationError(
                _("You can only pay on site when selecting the pick up in store delivery method.")
            )
