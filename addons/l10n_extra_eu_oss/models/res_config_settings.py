from odoo import api, fields, models
from .extra_eu_tax_map import EXTRA_EU_TAX_MAP


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_extra_eu_oss_extra_eu_country = fields.Boolean('Is non European OSS country?', compute='_compute_l10n_extra_eu_oss_extra_eu_country')

    def refresh_extra_eu_tax_mapping(self):
        self.env.companies._map_extra_eu_taxes()

    @api.depends('company_id')
    def _compute_l10n_extra_eu_oss_extra_eu_country(self):
        for record in self:
            record.l10n_extra_eu_oss_extra_eu_country = record.company_id.account_fiscal_country_id.code in [t[0] for t in EXTRA_EU_TAX_MAP]
