# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from .delivery import Delivery


class LocationSelector(Delivery):

    @route('/website_sale/get_pickup_locations', type='jsonrpc', auth='public', website=True)
    def website_sale_get_pickup_locations(self, res_model=None, res_id=None, **kwargs):
        """ Fetch the record or the order from the request and return the pickup locations close to a given zip code.

        :param str res_model: The model of the calling record, either `sale.order`, `stock.picking` or `choose.delivery.carrier`.
        :param int res_id: The id of the calling record.
        :return: The close pickup locations data.
        :rtype: dict
        """
        record = request.env[res_model].browse(res_id).sudo() if res_id else request.cart
        if request.geoip.country_code:
            country = request.env['res.country'].search(
                [('code', '=', request.geoip.country_code)], limit=1,
            )
        else:
            country = record.partner_id.country_id
        return record.carrier_id._get_pickup_locations(country=country, **kwargs)

    @route('/website_sale/set_pickup_location', type='jsonrpc', auth='public', website=True)
    def website_sale_set_pickup_location(self, pickup_location_data):
        """ Fetch the order from the request and set the pickup location on the current order.

        :param str pickup_location_data: The JSON-formatted pickup location address.
         :return: The order summary values.
        :rtype: dict
        """
        order_sudo = request.cart
        order_sudo.set_pickup_location(pickup_location_data)
        return self._order_summary_values(order_sudo)
