# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.sale_gelato import utils


class ProviderGelato(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('gelato', "Gelato")], ondelete={'gelato': 'cascade'}
    )
    gelato_shipping_service_type = fields.Selection(
        string="Gelato Shipping Service Type",
        selection=[('normal', "Standard Delivery"), ('express', "Express Delivery")],
        required=True,
        default='normal',
    )

    # === BUSINESS METHODS === #

    def _is_available_for_order(self, order):
        """ Override of `delivery` to exclude regular delivery methods from Gelato orders and Gelato
        delivery methods from non-Gelato orders.

        :param sale.order order: The current order.
        :return: Whether the delivery method is available for the order.
        :rtype: bool
        """
        is_gelato_order = any(order.order_line.product_id.mapped('gelato_product_uid'))
        is_gelato_delivery = self.delivery_type == 'gelato'
        if is_gelato_order and not is_gelato_delivery or not is_gelato_order and is_gelato_delivery:
            return False
        return super()._is_available_for_order(order)

    def available_carriers(self, partner, source):
        """ Override of `delivery` to filter out regular delivery methods from Gelato orders and
        Gelato delivery methods from non-Gelato orders.

        :param res.partner partner: The partner to check.
        :param sale.order or stock.picking source: The current order or stock transfer.
        :return: The available delivery methods.
        :rtype: delivery.carrier
        """
        available_delivery_methods = super().available_carriers(partner, source)
        if source._name == 'sale.order':
            is_gelato_order = any(source.order_line.product_id.mapped('gelato_product_uid'))
        elif source._name == 'stock.picking':
            is_gelato_order = any(source.move_ids.product_id.mapped('gelato_product_uid'))
        else:
            raise UserError(_("Invalid source document type"))
        if is_gelato_order:
            return available_delivery_methods.filtered(lambda m: m.delivery_type == 'gelato')
        else:
            return available_delivery_methods.filtered(lambda m: m.delivery_type != 'gelato')

    def gelato_rate_shipment(self, order):
        """ Fetch the Gelato delivery price based on products, quantity and address.

        This method is called by `delivery`'s `rate_shipment` method.

        Note: `self._ensure_one()` from `rate_shipment`

        :param sale.order order: The order for which to fetch the delivery price.
        :return: The shipment rate request results.
        :rtype: dict
        """
        if error_message := order._ensure_partner_address_is_complete():
            return {
                'success': False,
                'price': 0,
                'error_message': error_message,
            }

        # Fetch the delivery price from Gelato.
        payload = {
            'orderReferenceId': order.id,
            'customerReferenceId': f'Odoo Partner #{order.partner_id.id}',
            'currency': order.currency_id.name,
            'allowMultipleQuotes': 'true',
            'products': order._gelato_prepare_items_payload(),
            'recipient': order.partner_shipping_id._gelato_prepare_address_payload(),
        }
        try:
            api_key = order.company_id.sudo().gelato_api_key  # In sudo mode to read on the company.
            order_data = utils.make_request(api_key, 'order', 'v4', 'orders:quote', payload=payload)
        except UserError as e:
            return {
                'success': False,
                'price': 0,
                'error_message': str(e),
            }

        # Find the total delivery price by summing all products' matching methods' minimum price.
        total_delivery_price = 0
        for quote_data in order_data['quotes']:
            matching_shipment_method_prices = [
                shipment_method_data['price']
                for shipment_method_data in quote_data['shipmentMethods']
                if shipment_method_data['type'] == self.gelato_shipping_service_type
            ]
            if not matching_shipment_method_prices:
                return {
                    'success': False,
                    'price': 0,
                    'error_message': _("The delivery method is not available for this order."),
                }
            else:
                total_delivery_price += min(matching_shipment_method_prices)

        return {
            'success': True,
            'price': total_delivery_price,
        }
