# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortalExtended(CustomerPortal):
    def _prepare_address_form_values(self, partner_sudo, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(partner_sudo, *args, **kwargs)
        country = rendering_values['country']
        rendering_values.update({
            'city': partner_sudo.city_id,
            'state_cities': country._get_cities(state_id=rendering_values['state_id']),
        })
        return rendering_values

    def _get_mandatory_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_address_fields(country_sudo)
        if country_sudo._enforce_city_choice():
            mandatory_fields.add('city_id')
            mandatory_fields.remove('city')
        return mandatory_fields

    def _parse_form_data(self, form_data):
        address_values, extra_form_data = super()._parse_form_data(form_data)
        country_id = address_values.get('country_id')
        country_sudo = request.env['res.country'].browse(country_id)
        if country_sudo.enforce_cities and form_data.get('city_id'):
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
        country = state.country_id

        if country._enforce_city_choice():
            return {
                'cities': request.env['res.city'].sudo().search_read(
                    [('state_id', '=', state.id)],
                    country._get_cities_fields_to_fetch(),
                    load='',  # we only want the ids of relational fields
                )
            }

        return {
            'cities': [],
        }

    @route()
    def portal_address_country_info(self, country, address_type, **kw):
        res = super().portal_address_country_info(country, address_type, **kw)

        if country._enforce_city_choice():
            res['cities'] = country._get_cities().read(
                country._get_cities_fields_to_fetch(), load='',
            )

        return res
