# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.addons.website_sale.controllers.main import PaymentPortal
from odoo.exceptions import ValidationError
from odoo.http import request


class PaymentPortalOnsite(PaymentPortal):

    def _validate_transaction_for_order(self, transaction, sale_order_id):
        """
        Throws a ValidationError if the user tries to pay on site without also using an onsite delivery carrier
        Also sets the sale order's warehouse id to the carrier's if it exists
        """
        super()._validate_transaction_for_order(transaction, sale_order_id)
        sale_order = request.env['sale.order'].browse(sale_order_id).exists()

        # This should never be triggered unless the user intentionally forges a request.
        if sale_order.carrier_id.delivery_type != 'onsite' and (
            transaction.provider_id.code == 'custom'
            and transaction.provider_id.custom_mode == 'onsite'
        ):
            raise ValidationError(_("You cannot pay onsite if the delivery is not onsite"))

        if sale_order.carrier_id.delivery_type == 'onsite' and sale_order.carrier_id.warehouse_id:
            sale_order.warehouse_id = sale_order.carrier_id.warehouse_id
