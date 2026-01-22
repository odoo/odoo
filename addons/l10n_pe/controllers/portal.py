# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.l10n_latam_base.controllers.portal import L10nLatamBasePortalAccount


class L10nPEPortalAccount(L10nLatamBasePortalAccount):

    def _is_peru_company(self):
        return request.env.company.country_code == 'PE'

    def _prepare_address_form_values(self, partner_sudo, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(partner_sudo, *args, **kwargs)
        if self._is_peru_company():
            city = partner_sudo.city_id
            District = request.env['l10n_pe.res.city.district'].sudo()
            rendering_values.update({
                'city_districts': District.search([('city_id', '=', city.id)]) if city else District,
            })
        return rendering_values

    def _get_mandatory_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_address_fields(country_sudo)
        if self._is_peru_company() and country_sudo.code == 'PE':
            mandatory_fields.add('l10n_pe_district')
        return mandatory_fields

    def _l10n_get_default_identification_type_id(self):
        return (
            (self.env.company.country_code == 'PE' and request.env.ref('l10n_pe.it_DNI'))
            or super()._l10n_get_default_identification_type_id()
        )

    @route(
        '/portal/city_infos/<model("res.city"):city>',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
    )
    def city_infos(self, city, **kw):
        return {
            'districts': request.env['l10n_pe.res.city.district'].sudo().search_read(
                [('city_id', '=', city.id)], ['id', 'name', 'code']
            )
        }
