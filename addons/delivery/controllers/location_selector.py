# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route


class LocationSelectorController(Controller):

    @route('/delivery/get_pickup_locations', type='jsonrpc', auth='user')
    def delivery_get_pickup_locations(self, res_model, res_id, zip_code=None):
        """ Fetch the order and return the pickup locations close to a given zip code.

        Determine the country based on GeoIP or fallback on the order's delivery address' country.

        :param int order_id: The sales order, as a `sale.order` id.
        :param int zip_code: The zip code to look up to.
        :return: The close pickup locations data.
        :rtype: dict
        """
        record = request.env[res_model].browse(res_id)
        if request.geoip.country_code:
            country = request.env['res.country'].search(
                [('code', '=', request.geoip.country_code)], limit=1,
            )
        else:
            country = record.partner_id.country_id
        return record.carrier_id._get_pickup_locations(zip_code, country, parent_record=record)
