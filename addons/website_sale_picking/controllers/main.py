# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale
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

        # TODO should be managed in a `_compute_warehouse_id` or `update_eshop_carrier` override
        if sale_order.carrier_id.delivery_type == 'onsite' and sale_order.carrier_id.warehouse_id:
            sale_order.warehouse_id = sale_order.carrier_id.warehouse_id


class WebsiteSalePicking(WebsiteSale):

    def _check_shipping_partner_mandatory_fields(self, partner_id):
        order_sudo = request.website.sale_get_order()
        carrier_sudo = order_sudo.carrier_id
        if carrier_sudo.delivery_type == 'onsite' and partner_id == carrier_sudo.warehouse_id.partner_id:
            return True

        return super()._check_shipping_partner_mandatory_fields(partner_id)
