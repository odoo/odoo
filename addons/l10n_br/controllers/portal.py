# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.l10n_latam_base.controllers.portal import L10nLatamBasePortalAccount


class L10nBRPortalAccount(L10nLatamBasePortalAccount):

    def _is_brazilean_fiscal_country(self):
        return request.env.company.account_fiscal_country_id.code == 'BR'

    def _prepare_address_form_values(self, partner_sudo, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(partner_sudo, *args, **kwargs)
        if self._is_brazilean_fiscal_country():
            rendering_values.update({
                'city_sudo': partner_sudo.city_id,
                'cities_sudo': request.env['res.city'].sudo().search([
                    ('country_id.code', '=', 'BR'),
                ]),
            })
        return rendering_values

    def _get_mandatory_address_fields(self, country_sudo):
        mandatory_fields = super()._get_mandatory_address_fields(country_sudo)
        if country_sudo.code == 'BR' and self._is_brazilean_fiscal_country():
            mandatory_fields.update({
                'street_name', 'street2', 'street_number', 'city_id',
            })
            mandatory_fields -= {'street', 'city'}  # Brazil uses the base_extended_address fields added above

        return mandatory_fields
