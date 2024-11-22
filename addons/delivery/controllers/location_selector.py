# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route


class LocationSelectorController(Controller):

    @route('/delivery/set_pickup_location', type='jsonrpc', auth='user')
    def delivery_set_pickup_location(self, order_id, pickup_location_data):
        """ Fetch the order and set the pickup location on the current order.

        :param int order_id: The sales order, as a `sale.order` id.
        :param str pickup_location_data: The JSON-formatted pickup location address.
        :return: None
        """
        order = request.env['sale.order'].browse(order_id)
        order._set_pickup_location(pickup_location_data)

    @route('/delivery/get_pickup_locations', type='jsonrpc', auth='user')
    def delivery_get_pickup_locations(self, order_id, zip_code=None, country_code=None):
        """ Fetch the order and return the pickup locations close to a given zip code.

        Determine the country based on GeoIP or fallback on the order's delivery address' country.

        :param int order_id: The sales order, as a `sale.order` id.
        :param int zip_code: The zip code to look up to.
        :return: The close pickup locations data.
        :rtype: dict
        """
        order = request.env['sale.order'].browse(order_id)
        if request.geoip.country_code and not country_code:
            country_code = request.geoip.country_code
        return order._get_pickup_locations(zip_code, country_code=None)

    @route('/delivery/get_delivery_method_countries', type='jsonrpc', auth='public', website=True)
    def get_delivery_method_countries(self):
        """ Fetch the countries associated with a delivery carrier.

        Determine the country based the carrier selected on the order or fallback on the carrier
        of the website.

        :return: The available countries to select from.
        :rtype: dict
        """
        countries = None
        if order_sudo := request.cart:
            carrier_sudo = order_sudo.carrier_id
        elif website_sudo := request.website.sudo():
            # If no order was found then we are in click & collect in product page
            carrier_sudo = website_sudo.in_store_dm_id
        if carrier_sudo.country_ids:
            countries = carrier_sudo.country_ids
        else:
            if carrier_sudo.warehouse_ids:
                countries = carrier_sudo.warehouse_ids.partner_id.country_id
        if not countries:
            countries = request.env['res.country'].search_fetch(
                [], ['id', 'name', 'code', 'image_url']
            )
        return [
            {
                'value': {
                    'name': c.name,
                    'code': c.code,
                    'image_url': c.image_url,
                    'fields': c.get_address_fields(),
                },
                'label': c.name,
            } for c in countries
        ]
