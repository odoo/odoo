# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.exceptions import ValidationError


class WebsiteSaleController(WebsiteSale):

    def validate_transaction_for_order(self, transaction, sale_order):
        """
        If this is a payment for an onsite delivery : Automatically set the order as 'sale' since the payment is not awaited before preparing the order.
        Also sets the order shipping id to the delivery carrier's warehouse
        """
        super().validate_transaction_for_order(transaction, sale_order)

        # This should never be triggered unless the user intentionally forges a request.
        if transaction.acquirer_id.is_onsite_acquirer and sale_order.carrier_id.delivery_type != 'onsite':
            raise ValidationError(_('You cannot pay onsite if the delivery is not onsite'))

        if sale_order.carrier_id.delivery_type == 'onsite':
            sale_order.warehouse_id = sale_order.carrier_id.warehouse_id or sale_order.warehouse_id
            sale_order.partner_shipping_id = sale_order.warehouse_id.partner_id or sale_order.partner_shipping_id
