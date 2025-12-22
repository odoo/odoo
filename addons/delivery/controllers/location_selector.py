# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route


class LocationSelectorController(Controller):

    @route('/delivery/set_pickup_location', type='json', auth='user')
    def delivery_set_pickup_location(self, order_id, pickup_location_data):
        """ Fetch the order and set the pickup location on the current order.

        :param int order_id: The sales order, as a `sale.order` id.
        :param str pickup_location_data: The JSON-formatted pickup location address.
        :return: None
        """
        order = request.env['sale.order'].browse(order_id)
        order._set_pickup_location(pickup_location_data)

    @route('/delivery/get_pickup_locations', type='json', auth='user')
    def delivery_get_pickup_locations(self, order_id, zip_code=None):
        """ Fetch the order and return the pickup locations close to a given zip code.

        Determine the country based on GeoIP or fallback on the order's delivery address' country.

        :param int order_id: The sales order, as a `sale.order` id.
        :param int zip_code: The zip code to look up to.
        :return: The close pickup locations data.
        :rtype: dict
        """
        order = request.env['sale.order'].browse(order_id)
        if request.geoip.country_code:
            country = request.env['res.country'].search(
                [('code', '=', request.geoip.country_code)], limit=1,
            )
        else:
            country = order.partner_shipping_id.country_id
        return order._get_pickup_locations(zip_code, country)
