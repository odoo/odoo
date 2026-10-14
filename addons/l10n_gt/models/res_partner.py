# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models

from odoo.addons.l10n_gt.tools.partner_identifiers import GT_ADDITIONAL_IDENTIFIERS_METADATA


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **GT_ADDITIONAL_IDENTIFIERS_METADATA}

    @api.model
    def _get_portal_additional_identifiers(self, country_sudo, **kwargs):
        optional, mandatory = super()._get_portal_additional_identifiers(country_sudo, **kwargs)
        if self.env.company.account_fiscal_country_id.code == 'GT' and country_sudo.code == 'GT':
            optional.add('GT_CUI')
        return optional, mandatory
