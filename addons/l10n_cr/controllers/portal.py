from odoo.http import request, route

from odoo.addons.account.controllers.portal import PortalAccount


class L10nCRPortalAccount(PortalAccount):

    def _prepare_address_form_values(self, partner_sudo, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(partner_sudo, *args, **kwargs)
        if rendering_values['country'].code == 'CR':
            rendering_values['l10n_cr_city_districts'] = self._l10n_cr_get_districts(
                rendering_values['city'].id, rendering_values['state'].id,
            )
        return rendering_values

    def _l10n_cr_get_districts(self, city_id=None, state_id=None):
        """Return the districts of the cantón, else of the province, else of all Costa Rica."""
        if city_id:
            domain = [('city_id', '=', city_id)]
        elif state_id:
            domain = [('city_id.state_id', '=', state_id)]
        else:
            domain = [('city_id.country_id.code', '=', 'CR')]
        return [
            {'id': district.id, 'name': district.display_name, 'cityId': district.city_id.id, 'stateId': district.city_id.state_id.id}
            for district in request.env['l10n_cr.res.city.district'].sudo().search(domain)
        ]

    @route(
        '/my/address/l10n_cr_districts',
        type='jsonrpc',
        auth='public',
        methods=['POST'],
        website=True,
        readonly=True,
    )
    def l10n_cr_districts(self, city_id=None, state_id=None):
        return self._l10n_cr_get_districts(city_id, state_id)
