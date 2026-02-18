# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.delivery import WebsiteSaleDelivery

from odoo.exceptions import AccessDenied, UserError
from odoo.http import request


class DeliveryShipper(http.Controller):

    @http.route(['/delivery_shipper/update_shipping_rate'], type='json', auth="public", website=True)
    def update_shipping_rate(self, rate_id, rate_price, rate_name):
        """
        Update the shipping method on the order and apply the selected rate.
        """
        order = request.website.sale_get_order()
        if not order:
            return {'error': 'No active order'}

        # Validate the carrier based on the rate_id
        carrier = request.env['delivery.carrier'].sudo().search([('id', '=', 7)], limit=1)
        if not carrier:
            return {'error': 'Invalid rate selected'}
        carrier.shipper_rate_shipment(order, from_website=True)

        # # Update the carrier and set the delivery line
        # order.write({'carrier_id': carrier.id})
        # order.set_delivery_line(carrier, float(rate_price))

        # # Customize the delivery line's description
        # delivery_line = order.order_line.filtered(
        #     lambda line: line.is_delivery and line.product_id == carrier.product_id
        # )[-1]
        # if delivery_line:
        #     delivery_line.name = f"[{rate_name}] {carrier.name}"

        return {'success': True, 'message': 'Shipping rate updated successfully'}


class WebsiteSaleDeliveryShipper(WebsiteSaleDelivery):

    def _update_website_sale_delivery_return(self, order, **post):
        res = super()._update_website_sale_delivery_return(order, **post)
        if order.carrier_id.delivery_type == 'shipper':
            res['is_shipper'] = True
            rates = order.carrier_id.get_shipper_rate(order)
            res['shipper_rates'] = [{
                'rate_id': rate['rate_id'],
                'carrier_name': rate['carrier_name'],
                'service': rate['service'],
                'final_price': rate['final_price'],
                'delivery_time': rate['delivery_time'],
            } for rate in rates]
        return res
