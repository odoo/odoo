# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_delivery_carrier_id = fields.Many2one('delivery.carrier', company_dependent=True, string="Delivery Method", help="Used in sales orders.")
    pickup_delivery_carrier_id = fields.Many2one('delivery.carrier', ondelete='cascade')  # The delivery method that generated this pickup location.
    pickup_location_data = fields.Json()  # Technical field: information needed by shipping providers in case of pickup point addresses.

    def _is_address_usable(self):
        """ Override to prevent using pickup locations as regular delivery addresses. """
        return super()._is_address_usable() and not self.pickup_delivery_carrier_id

    def _get_delivery_address_domain(self):
        return super()._get_delivery_address_domain() & Domain('pickup_delivery_carrier_id', '=', False)

    @api.model
    def _address_from_json(self, json_location_data, parent_id, pickup_delivery_carrier_id=False):
        """ Searches for an existing address with the same data as the one in json_location_data
        and the same parent_id. If no address is found, creates a new one.

        :param dict json_location_data: The location data in JSON format returned by the carrier's API.
        :param res.partner parent_id: The parent partner of the address to create.
        :param str pickup_delivery_carrier_id: The type of the delivery method that generated this pickup location.
        :return: The existing or newly created address.
        :rtype: res.partner
        """
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
                ('pickup_delivery_carrier_id', '=', pickup_delivery_carrier_id)
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
                    'pickup_delivery_carrier_id': pickup_delivery_carrier_id,
                    'pickup_location_data': json_location_data,
                })
        return self.env['res.partner']
