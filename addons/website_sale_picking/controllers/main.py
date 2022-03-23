from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.exceptions import UserError


class WebsiteSaleController(WebsiteSale):

    def validate_transaction_for_order(self, transaction, sale_order):
        """
        If this is a payment for an onsite delivery : Automatically set the order as 'sale' since the payment is not awaited before preparing the order.
        Also sets the order shipping id to the delivery carrier's warehouse
        """
        super().validate_transaction_for_order(transaction, sale_order)

        if transaction.acquirer_id.is_onsite_acquirer and sale_order.carrier_id.delivery_type != 'onsite':
            raise UserError('You cannot pay onsite if the delivery is not onsite')  # This should never be triggered unless the user intentionally forges a request.

        if sale_order.carrier_id.delivery_type == 'onsite':
            sale_order.state = 'sale'
            if sale_order.carrier_id.warehouse_id:
                sale_order.warehouse_id = sale_order.carrier_id.warehouse_id
                if sale_order.warehouse_id.partner_id:
                    sale_order.partner_shipping_id = sale_order.warehouse_id.partner_id
