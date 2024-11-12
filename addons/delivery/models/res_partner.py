# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = ['res.partner']

    property_delivery_carrier_id = fields.Many2one('delivery.carrier', company_dependent=True, string="Delivery Method", help="Default delivery method used in sales orders.")
    location_data = fields.Json(help="Information needed by shipping providers in case of pickup point addresses.")

    @api.model
    def _address_from_json(self, json_location_data, parent_id):
        """ Searches for an existing address with the same data as the one in json_location_data
        and the same parent_id. If no address is found, creates a new one. """
        location_data = json.loads(json_location_data)
        if location_data:
            name = location_data['name']
            street = location_data['street']
            city = location_data['city']
            zip_code = location_data['zip_code']
            country_code = location_data['country_code']
            country = self.env['res.country'].search([('code', '=', country_code)]).id
            state = self.env['res.country.state'].search([
                ('code', '=', location_data['state']),
                ('country_id', '=', country),
            ]).id if (location_data.get('state') and country) else None

            domain = [
                ('name', '=', name),
                ('street', '=', street),
                ('city', '=', city),
                ('state_id', '=', state),
                ('country_id', '=', country),
                ('type', '=', 'delivery'),
                ('parent_id', '=', parent_id.id),
            ]
            existing_partner = self.env['res.partner'].search(domain, limit=1)
            if existing_partner:
                return existing_partner
            else:
                return self.env['res.partner'].create({
                    'name': name,
                    'type': 'delivery',
                    'street': street,
                    'city': city,
                    'state_id': state,
                    'zip': zip_code,
                    'country_id': country,
                    'location_data': location_data,
                    'parent_id': parent_id.id,
                })
        return False
