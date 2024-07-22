# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request
from odoo.exceptions import ValidationError

from odoo.addons.website_sale.controllers.main import WebsiteSale as WebsiteSaleController
from odoo.addons.website_sale.controllers.payment import PaymentPortal


class PaymentPortalOnsite(PaymentPortal):

    def _validate_transaction_for_order(self, transaction, sale_order):
        """ Override of `website_sale `to make sure the onsite provider is not used without
        the onsite carrier.
        Also sets the sale order's warehouse id to the carrier's if it exists

        :raises ValidationError: if the user tries to pay on site without the matching delivery carrier
        """
        super()._validate_transaction_for_order(transaction, sale_order)

        # This should never be triggered unless the user intentionally forges a request.
        provider = transaction.provider_id
        if (
            sale_order.carrier_id.delivery_type != 'onsite'
            and provider.code == 'custom'
            and provider.custom_mode == 'onsite'
        ):
            raise ValidationError(_("You cannot pay onsite if the delivery is not onsite"))
        if sale_order.carrier_id.delivery_type == 'onsite':
            selected_wh_id = sale_order.pickup_location_data['warehouse_id']
            if not sale_order._is_cart_in_stock(selected_wh_id):
                raise ValidationError(
                    _("You can not pay as some products are not available in the selected store")
                )
            sale_order.warehouse_id = sale_order.env['stock.warehouse'].browse(selected_wh_id)
