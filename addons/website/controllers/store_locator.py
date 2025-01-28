# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import logging

from odoo import http
from odoo.http import Controller, request, route


_logger = logging.getLogger(__name__)


class StoreLocatorController(Controller):

    @http.route('/website/get_locations', type='jsonrpc', auth='public', website=True, readonly=True)
    def website_get_locations(self):
        store_locations_data = request.env['res.partner'].search_read(
            domain = ['&', ('contact_address_complete', '!=', "''"), ('is_company', '=', True)],
            fields = ["commercial_company_name", "street", "city", "zip", "country_id", "partner_latitude", "partner_longitude", "phone", "email"],
        )

        #Get latitude and longitude from openstreetmap API
        #TODO handle errors
        #TODO save found latitude and longitude to DB ?
        for location in store_locations_data:
            if not location['partner_latitude'] or not location['partner_latitude']:
                try:
                    url = 'https://nominatim.openstreetmap.org/search'
                    headers = {'User-Agent': 'Odoo (http://www.odoo.com/contactus)'}
                    #TODO security issue ?
                    addr = " ".join((location['street'], location['city'], location['zip'], location['country_id'][1]))
                    response = requests.get(url, headers=headers, params={'format': 'json', 'q': addr})
                    _logger.info('openstreetmap nominatim service called')
                    if response.status_code != 200:
                        _logger.warning('Request to openstreetmap failed.\nCode: %s\nContent: %s', response.status_code, response.content)
                    result = response.json()
                    if result:
                        location['partner_latitude'] = float(result[0]['lat'])
                        location['partner_longitude'] = float(result[0]['lon'])
                except Exception as e:
                    self._raise_query_error(e)

        return store_locations_data
