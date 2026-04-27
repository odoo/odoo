# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from .sendcloud_locations_request import SendcloudLocationsRequest

# As Sendcloud API's schemas may evolve, hardcoded values are defined as static const to ease futur updates.
# _T stands for sendcloud technical names while _H define 'humanized' name
LAST_MILE_T = 'last_mile'
LAST_MILE_SERVICES_T = ['service_point', 'locker', 'locker_or_service_point']
LAST_MILE_H = 'Last mile'
LAST_MILE_SERVICES_H = ['Service point', 'Locker', 'Locker or service point']


class ProviderSendcloud(models.Model):
    _inherit = 'delivery.carrier'

    sendcloud_can_customize_use_locations = fields.Boolean(default=False, compute='_compute_sendcloud_can_customize_use_locations')
    sendcloud_use_locations = fields.Boolean(string='Use Sendcloud Locations',
                                             help='Allows the ecommerce user to choose a pick-up point as delivery address.',
                                             default=False, compute='_compute_sendcloud_use_locations', store=True)
    sendcloud_locations_radius_value = fields.Integer(string='Sendcloud Locations Radius',
                                                      help='Maximum locations distance radius.',
                                                      default=10, required=True)
    sendcloud_locations_radius_unit = fields.Many2one('uom.uom', compute='_compute_sendcloud_locations_radius_unit',
                                                      default=lambda self: self.env.ref('uom.product_uom_km'), search='_search_sendcloud_locations_radius_unit', store=True)
    sendcloud_locations_radius_unit_name = fields.Char('Sendcloud Radius Unit Name', related='sendcloud_locations_radius_unit.display_name')
    sendcloud_locations_id = fields.Integer(string='Locations Id')

    @api.depends('sendcloud_shipping_id')
    def _compute_sendcloud_can_customize_use_locations(self):
        self.sendcloud_can_customize_use_locations = False
        for sc_carrier in self:
            product_func = sc_carrier.sendcloud_shipping_id.functionalities
            if not product_func:
                continue
            last_mile_custo = product_func.get('customizable', {}).get(LAST_MILE_T)
            # N.B. if last_mile is set, then it has at least a length of 2 as it appears in 'customizable'
            if last_mile_custo and any(service in last_mile_custo for service in LAST_MILE_SERVICES_T):
                # service point is available but not mandatory, let the user choose
                sc_carrier.sendcloud_can_customize_use_locations = True

    @api.depends('sendcloud_shipping_id')
    def _compute_sendcloud_use_locations(self):
        for sc_carrier in self:
            product_func = sc_carrier.sendcloud_shipping_id.functionalities
            if not product_func:
                sc_carrier.sendcloud_use_locations = False
                continue
            if not sc_carrier.sendcloud_can_customize_use_locations and any(service in product_func.get('detail_func', {}).get(LAST_MILE_H, {}) for service in LAST_MILE_SERVICES_H):
                sc_carrier.sendcloud_use_locations = True
            else:
                sc_carrier.sendcloud_use_locations = False

    def _compute_sendcloud_locations_radius_unit(self):
        for carrier in self:
            carrier.sendcloud_locations_radius_unit = self._get_distance_uom_id_from_ir_config_parameter()

    @api.model
    def _get_distance_uom_id_from_ir_config_parameter(self):
        distance_in_miles_param = self.env['ir.config_parameter'].sudo().get_param('product.volume_in_cubic_feet')
        if distance_in_miles_param == '1':
            return self.env.ref('uom.product_uom_mile')
        return self.env.ref('uom.product_uom_km')

    def _search_sendcloud_locations_radius_unit(self, operator, value):
        return [('sendcloud_locations_radius_value', operator, value)]

    @api.constrains("sendcloud_locations_radius_value")
    def _check_radius_value(self):
        uom_meter = self.env.ref('uom.product_uom_meter')
        for delivery in self:
            distance_meters = delivery.sendcloud_locations_radius_unit._compute_quantity(delivery.sendcloud_locations_radius_value, uom_meter)

            if distance_meters > 50000:
                # maximum distance to display in that specific unit
                max_distance = uom_meter._compute_quantity(50000, delivery.sendcloud_locations_radius_unit)
                raise ValidationError(_("The maximum radius allowed is %(distance)d%(unit)s", distance=max_distance, unit=delivery.sendcloud_locations_radius_unit.name))

            if distance_meters < 100:
                # minimum distance to display in that specific unit
                min_distance = uom_meter._compute_quantity(100, delivery.sendcloud_locations_radius_unit)
                raise ValidationError(_("The minimum radius allowed is %(distance)d%(unit)s", distance=min_distance, unit=delivery.sendcloud_locations_radius_unit.name))

    def _sendcloud_get_close_locations(self, partner_address):
        superself = self.sudo()
        distance = int(self.sendcloud_locations_radius_unit._compute_quantity(self.sendcloud_locations_radius_value, self.env.ref('uom.product_uom_meter')))
        slr = SendcloudLocationsRequest(superself.sendcloud_public_key, superself.sendcloud_secret_key, self.log_xml)

        locations = slr.get_close_locations(partner_address, distance, self.sendcloud_shipping_id.carrier)
        close_locations = []

        for location in locations:
            close_locations.append(dict(
                id=location['id'],
                name=location['name'].title(),
                opening_hours=location['formatted_opening_times'],
                street=f"{location['street'].title()} {location['house_number']}",
                city=location['city'].title(),
                zip_code=location['postal_code'],
                country_code=location['country'],
                latitude=location['latitude'],
                longitude=location['longitude'],
            ))

        return close_locations
