# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.delivery_sendcloud.models.sendcloud_service import SendCloud

LOCATION_URL = "https://servicepoints.sendcloud.sc/api/v2/"


class SendcloudLocationsRequest(SendCloud):

    def get_close_locations(self, partner_address, distance, carrier):
        if carrier == 'sendcloud':
            carrier = ''
        params = {"country": partner_address.country_code,
                  "address": f'{partner_address.zip} {partner_address.city}',
                  "radius": distance,
                  "carrier": carrier}
        return self._send_request('service-points', params=params, route=LOCATION_URL)
