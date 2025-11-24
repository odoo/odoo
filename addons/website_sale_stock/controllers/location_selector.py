# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_sale.controllers.delivery import Delivery


class LocationSelector(Delivery):
    @route("/website_sale_stock/get_pickup_locations", type="jsonrpc", auth="public", website=True)
    def website_sale_get_pickup_locations(self, delivery_method_id=None, country_id=None, **kwargs):
        """Return the pickup locations of the delivery method.

        :param int delivery_method_id: ID of the selected delivery method.
        :param int country_id: ID of the country to look for pickup locations in
        :return: The closest pickup locations' data.
        :rtype: dict
        """
        if order_sudo := request.cart:  # Request from frontend
            delivery_method = order_sudo.carrier_id
            country = order_sudo.partner_shipping_id.country_id
        else:  # From the backend
            delivery_method = request.env["delivery.carrier"].sudo().browse(delivery_method_id)
            country = request.env["res.country"].browse(country_id)

        if not delivery_method:
            return {}

        return delivery_method._get_pickup_locations(country=country, **kwargs)

    @route("/website_sale_stock/set_pickup_location", type="jsonrpc", auth="public", website=True)
    def website_sale_set_pickup_location(self, pickup_location_data):
        """Fetch the order from the request and set the pickup location on the current order.

        :param str pickup_location_data: The JSON-formatted pickup location address.
        :return: The order summary values.
        :rtype: dict
        """
        order_sudo = request.cart
        order_sudo.set_pickup_location(pickup_location_data)
        return self._order_summary_values(order_sudo)
