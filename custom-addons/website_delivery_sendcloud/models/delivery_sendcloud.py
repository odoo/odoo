# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from .sendcloud_locations_request import SendcloudLocationsRequest

# As Sendcloud API's schemas may evolve, hardcoded values are defined as static const to ease futur updates.
# _T stands for sendcloud technical names while _H define 'humanized' name
LAST_MILE_T = 'last_mile'
SERVICE_POINT_T = 'service_point'
LAST_MILE_H = 'Last mile'
SERVICE_POINT_H = 'Service point'


class ProviderSendcloud(models.Model):
    _inherit = 'delivery.carrier'

    def _radius_unit_domain(self):
        categ_length_id = (self.env.ref("uom.uom_categ_length")).id
        if categ_length_id:
            return [('category_id.id', '=', categ_length_id)]
        return []

    sendcloud_can_customize_use_locations = fields.Boolean(default=False, compute='_compute_sendcloud_can_customize_use_locations')
    sendcloud_use_locations = fields.Boolean(string='Use Sendcloud Locations',
                                             help='Allows the ecommerce user to choose a pick-up point as delivery address.',
                                             default=False, compute='_compute_sendcloud_use_locations', store=True)
    sendcloud_locations_radius_value = fields.Integer(string='Locations Distance Radius',
                                                      help='Maximum locations distance radius.',
                                                      default=1500, required=True)
    sendcloud_locations_radius_unit = fields.Many2one('uom.uom',
                                                      string='Distance Unit',
                                                      domain=_radius_unit_domain,
                                                      default=lambda self: self.env.ref("uom.product_uom_meter"))
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
            if last_mile_custo and SERVICE_POINT_T in last_mile_custo:
                # service point is available but not mandatory, let the user choose
                sc_carrier.sendcloud_can_customize_use_locations = True

    @api.depends('sendcloud_shipping_id')
    def _compute_sendcloud_use_locations(self):
        for sc_carrier in self:
            product_func = sc_carrier.sendcloud_shipping_id.functionalities
            if not product_func:
                sc_carrier.sendcloud_use_locations = False
                continue
            if not sc_carrier.sendcloud_can_customize_use_locations and SERVICE_POINT_H in product_func.get('detail_func', {}).get(LAST_MILE_H, {}):
                # the only available option is service point
                sc_carrier.sendcloud_use_locations = True
            else:
                sc_carrier.sendcloud_use_locations = False

    @api.constrains("sendcloud_locations_radius_value", "sendcloud_locations_radius_unit")
    def _check_radius_value(self):
        uom_meter = self.env.ref('uom.product_uom_meter')
        for delivery in self:
            distance_meters = delivery.sendcloud_locations_radius_unit._compute_quantity(delivery.sendcloud_locations_radius_value, uom_meter)

            if distance_meters > 50000:
                # maximum distance to display in that specific unit
                max_distance = uom_meter._compute_quantity(50000, delivery.sendcloud_locations_radius_unit)
                raise ValidationError(_("The maximum radius allowed is %d%s", max_distance, delivery.sendcloud_locations_radius_unit.name))

            if distance_meters < 100:
                # minimum distance to display in that specific unit
                min_distance = uom_meter._compute_quantity(100, delivery.sendcloud_locations_radius_unit)
                raise ValidationError(_("The minimum radius allowed is %d%s", min_distance, delivery.sendcloud_locations_radius_unit.name))

    def _sendcloud_get_close_locations(self, partner_address):
        superself = self.sudo()
        distance = int(self.sendcloud_locations_radius_unit._compute_quantity(self.sendcloud_locations_radius_value, self.env.ref('uom.product_uom_meter')))
        slr = SendcloudLocationsRequest(superself.sendcloud_public_key, superself.sendcloud_secret_key, self.log_xml)

        locations = slr.get_close_locations(partner_address, distance, self.sendcloud_shipping_id.carrier)

        for location in locations:
            location["address"] = f'{location["street"]} {location["house_number"]}, {location["city"]} ({location["postal_code"]})'
            location["pick_up_point_name"] = location["name"]
            location["pick_up_point_address"] = f'{location["street"]} {location["house_number"]}'
            location["pick_up_point_postal_code"] = location["postal_code"]
            location["pick_up_point_town"] = location["city"]
            location["pick_up_point_country"] = location["country"]
            location["pick_up_point_state"] = None
        return locations
