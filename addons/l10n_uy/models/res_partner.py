# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models

from odoo.addons.l10n_uy.tools.partner_identifiers import (
    DGI_FOREIGN_COUNTRY_CODES,
    UY_ADDITIONAL_IDENTIFIERS_METADATA,
)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **UY_ADDITIONAL_IDENTIFIERS_METADATA}

    @api.model
    def _get_portal_additional_identifiers(self, country_sudo, **kwargs):
        optional, mandatory = super()._get_portal_additional_identifiers(country_sudo, **kwargs)
        if self.env.company.account_fiscal_country_id.code == 'UY':
            optional.add('PASSPORT')
            if country_sudo.code == 'UY':
                optional.update({'UY_CI', 'UY_NIE'})
            elif country_sudo.code in DGI_FOREIGN_COUNTRY_CODES:  # The DNI is the document of a Mercosur national.
                optional.add('UY_DNI')
        return optional, mandatory
