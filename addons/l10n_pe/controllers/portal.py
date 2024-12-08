# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.l10n_latam_base.controllers.portal import L10nLatamBasePortalAccount


class L10nPEPortalAccount(L10nLatamBasePortalAccount):

    def _is_peru_company(self):
        return request.env.company.country_code == 'PE'

    def _prepare_address_form_values(self, partner_sudo, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(partner_sudo, *args, **kwargs)
        if not self._is_peru_company():
            return rendering_values

        state = request.env['res.country.state'].browse(rendering_values['state_id'])
        city = partner_sudo.city_id
        ResCity = request.env['res.city'].sudo()
        District = request.env['l10n_pe.res.city.district'].sudo()
        rendering_values.update({
            'state': state,
            'state_cities': ResCity.search([('state_id', '=', state.id)]) if state else ResCity,
            'city': city,
            'city_districts': District.search([('city_id', '=', city.id)]) if city else District,
        })
        return rendering_values

    def _get_mandatory_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_address_fields(country_sudo)
        if not self._is_peru_company():
            return mandatory_fields

        if country_sudo.code == 'PE':
            mandatory_fields.update({'state_id', 'city_id', 'l10n_pe_district'})
            mandatory_fields.remove('city')
        return mandatory_fields

    def _l10n_get_default_identification_type_id(self):
        return (
            (self.env.company.country_code == 'PE' and request.env.ref('l10n_pe.it_DNI'))
            or super()._l10n_get_default_identification_type_id()
        )

    @route(
        '/portal/state_infos/<model("res.country.state"):state>',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def state_infos(self, state, **kw):
        states = request.env['res.city'].sudo().search([('state_id', '=', state.id)])
        return {'cities': [(c.id, c.name, c.l10n_pe_code) for c in states]}

    @route(
        '/portal/city_infos/<model("res.city"):city>',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def city_infos(self, city, **kw):
        districts = request.env['l10n_pe.res.city.district'].sudo().search(
            [('city_id', '=', city.id)],
        )
        return {'districts': [(d.id, d.name, d.code) for d in districts]}
