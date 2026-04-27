# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import fields, models
from .fedex_locations_request import FEDEXLocationsRequest


class ProviderFedex(models.Model):
    _inherit = 'delivery.carrier'

    fedex_use_locations = fields.Boolean(string='Use Fedex Locations', help='Allows the ecommerce user to choose a pick-up point as delivery address.')
    fedex_locations_radius_value = fields.Integer(string='Fedex Locations Radius', help='Maximum locations distance radius.', default=15, required=True)
    fedex_locations_radius_unit = fields.Many2one('uom.uom', compute='_compute_fedex_locations_radius_unit', search='_search_fedex_locations_radius_unit', store=True)
    fedex_locations_radius_unit_name = fields.Char('Fedex Radius Unit Name', related='fedex_locations_radius_unit.display_name')

    def _compute_fedex_locations_radius_unit(self):
        for carrier in self:
            carrier.fedex_locations_radius_unit = self._get_distance_uom_id_from_ir_config_parameter()

    def _search_fedex_locations_radius_unit(self, operator, value):
        return [('name', operator, value)]

    def _get_distance_uom_id_from_ir_config_parameter(self):
        distance_in_miles_param = self.env['ir.config_parameter'].sudo().get_param('product.volume_in_cubic_feet')
        if distance_in_miles_param == '1':
            return self.env.ref('uom.product_uom_mile')
        return self.env.ref('uom.product_uom_km')

    def _fedex_get_close_locations(self, partner_address):
        superself = self.sudo()
        srm = FEDEXLocationsRequest(self.log_xml, request_type="locs", prod_environment=self.prod_environment)
        srm.web_authentication_detail(superself.fedex_developer_key, superself.fedex_developer_password)
        srm.client_detail(superself.fedex_account_number, superself.fedex_meter_number)
        srm.transaction_detail('Location Request zip_code=%s' % partner_address.zip)
        srm.set_locs_details(self, partner_address)
        locations = srm.process_locs()
        close_locations = []

        for location in locations:
            address = location['LocationDetail']['LocationContactAndAddress']['Address']
            contact = location['LocationDetail']['LocationContactAndAddress']['Contact']
            name = contact['CompanyName'] if contact else location['LocationDetail']['LocationTypeForDisplay']
            latitude, longitude = re.compile(r'([-+]\d+\.\d+)([-+]\d+\.\d+)').match(
                address['GeographicCoordinates']
            ).groups()

            close_locations.append(dict(
                id=location['LocationDetail']['LocationId'],
                name=name,
                opening_hours=self._fedex_format_opening_hours(
                    location['LocationDetail']['HoursForEffectiveDate']
                ),
                street=address['StreetLines'][0],
                city=address['City'].title(),
                zip_code=address['PostalCode'],
                state=address['StateOrProvinceCode'],
                country_code=address['CountryCode'],
                additional_data=dict(
                    location_detail=location['LocationDetail'],
                ),
                latitude=latitude,
                longitude=longitude,
            ))

        return close_locations

    def _fedex_update_srm(self, srm, request_type, order=None, picking=None):
        """Add alternate delivery address to the shipment."""
        res = super(ProviderFedex, self)._fedex_update_srm(srm, request_type, order, picking)
        if picking:
            order = picking.sale_id
        if order and order.pickup_location_data:
            pickup_location_data = order.pickup_location_data or {}
            fedex_loc_details = pickup_location_data.get('additional_data', {}).get('location_detail', {})

            hold_at_loc = srm.factory.HoldAtLocationDetail()
            hold_at_loc.PhoneNumber = order.partner_shipping_id.phone
            hold_at_loc.LocationContactAndAddress = fedex_loc_details.get('LocationContactAndAddress', {})
            if 'AddressAncillaryDetail' in hold_at_loc.LocationContactAndAddress:
                del hold_at_loc.LocationContactAndAddress['AddressAncillaryDetail']
            hold_at_loc.LocationType = fedex_loc_details.get('LocationType')
            hold_at_loc.LocationId = fedex_loc_details.get('LocationId')

            srm.RequestedShipment.SpecialServicesRequested.HoldAtLocationDetail = hold_at_loc
        return res

    def _fedex_format_opening_hours(self, opening_hours):
        formatted_opening_hours = dict()
        for day, opening_hour in enumerate(opening_hours):
            # An alternative could be the usage of:
            # format_time(self.env,'2000-01-01 08:00:00', tz="UTC", time_format="short")
            # but it adds AM or PM at the end of the time frame
            formatted_opening_hours[day] = [
                o['Begins'][:-3] + " - " + o['Ends'][:-3] for o in opening_hour['Hours']
            ]
        return formatted_opening_hours
