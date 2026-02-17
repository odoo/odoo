# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.portal_address_extended.controllers.portal import CustomerPortalExtended


class L10nBRPortalAccount(CustomerPortalExtended):

    def _is_brazilean_fiscal_country(self):
        return request.env.company.account_fiscal_country_id.code == 'BR'

    def _get_mandatory_address_fields(self, country_sudo, **kwargs):
        mandatory_fields = super()._get_mandatory_address_fields(country_sudo, **kwargs)
        if country_sudo.code == 'BR' and self._is_brazilean_fiscal_country():
            mandatory_fields.update({
                'street_name', 'street2', 'street_number',
            })
            mandatory_fields.remove('street')

        return mandatory_fields
