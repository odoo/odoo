# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortalExtended(CustomerPortal):

    def _is_enforce_cities(self):
        return request.env.company.country_id.enforce_cities

    def _prepare_address_form_values(self, partner_sudo, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(partner_sudo, *args, **kwargs)
        if self._is_enforce_cities():
            state_cities = request.env['res.city'].sudo().search([
                ('country_id', '=', partner_sudo.country_id.id),
            ])
            rendering_values.setdefault('city', partner_sudo.city_id)
            rendering_values.setdefault('state_cities', state_cities)
        return rendering_values

    def _get_mandatory_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_address_fields(country_sudo)
        if self._is_enforce_cities() and country_sudo.enforce_cities:
            mandatory_fields.add('city_id')
            mandatory_fields.remove('city')
        return mandatory_fields

    def _parse_form_data(self, form_data):
        address_values, extra_form_data = super()._parse_form_data(form_data)
        country_id = address_values.get('country_id')
        country_sudo = request.env['res.country'].browse(country_id)
        if country_sudo.enforce_cities and self._is_enforce_cities() and form_data.get('city_id'):
            if city := request.env['res.city'].sudo().browse(int(form_data['city_id'])):
                address_values['city'] = city.name
        return address_values, extra_form_data

    @route(
        '/my/address/state_info/<model("res.country.state"):state>',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        readonly=True,
    )
    def portal_address_state_info(self, state, **kw):
        cities = request.env['res.city'].sudo().search([('state_id', '=', state.id)])
        return {'cities': [(city.id, city.name) for city in cities]}
