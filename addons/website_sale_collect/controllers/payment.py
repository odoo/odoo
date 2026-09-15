from odoo import _
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_sale.controllers.payment import PaymentPortal

_debug = DebugLog(__name__)


class OnSitePaymentPortal(PaymentPortal):
    def _check_transaction_for_order(self, transaction, sale_order):
        super()._check_transaction_for_order(transaction, sale_order)

        provider = transaction.provider_id
        if (
            sale_order.carrier_id.delivery_type != "in_store"
            and provider.code == "custom"
            and provider.custom_mode == "on_site"
        ):
            _debug.logic("in_store_payment_refused", provider=provider.id)
            raise ValidationError(
                _(
                    "You can only pay on site when selecting the pick up in store delivery method."
                )
            )
