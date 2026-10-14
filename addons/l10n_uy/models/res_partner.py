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
    def _get_portal_additional_identifiers_whitelist(self, company=None, country=None):
        whitelist = super()._get_portal_additional_identifiers_whitelist(company=company, country=country)
        if company and company.account_fiscal_country_id.code == 'UY':
            whitelist.add('PASSPORT')
            if country and country.code == 'UY':
                whitelist.update({'UY_CI', 'UY_NIE'})
            elif country and country.code in DGI_FOREIGN_COUNTRY_CODES:  # The DNI is the document of a Mercosur national.
                whitelist.add('UY_DNI')
        return whitelist
