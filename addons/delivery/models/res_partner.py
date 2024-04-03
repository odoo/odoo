# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_delivery_carrier_id = fields.Many2one('delivery.carrier', company_dependent=True, string="Delivery Method", help="Used in sales orders.")
    is_pickup_location = fields.Boolean()  # Whether it is a pickup point address.
    location_data = fields.Json(help="Information needed by shipping providers in case of pickup point addresses.")

    def _get_delivery_address_domain(self):
        return super()._get_delivery_address_domain() & Domain('is_pickup_location', '=', False)

    @api.model
    def _address_from_json(self, json_location_data, parent_id, is_pickup_location=True):
        """ Searches for an existing address with the same data as the one in json_location_data
        and the same parent_id. If no address is found, creates a new one. """
        if json_location_data:
            name = json_location_data.get('name', False)
            street = json_location_data.get('street', False)
            city = json_location_data.get('city', False)
            zip_code = json_location_data.get('zip_code', False)
            country_code = json_location_data.get('country_code', False)
            country = self.env['res.country'].search([('code', '=', country_code)]).id
            state = self.env['res.country.state'].search([
                ('code', '=', json_location_data.get('state', False)),
                ('country_id', '=', country),
            ]).id if (json_location_data.get('state') and country) else None
            email = json_location_data.get('email', parent_id.email)
            phone = json_location_data.get('phone', parent_id.phone)

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
                    'parent_id': parent_id.id,
                    'type': 'delivery',
                    'name': name,
                    'street': street,
                    'city': city,
                    'state_id': state,
                    'zip': zip_code,
                    'country_id': country,
                    'email': email,
                    'phone': phone,
                    'is_pickup_location': is_pickup_location,
                    'location_data': json_location_data,
                })
        return self.env['res.partner']
