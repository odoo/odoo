# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_eu_oss_eu_country = fields.Boolean('Is European country?', compute='_compute_l10n_eu_oss_european_country')

    def refresh_eu_tax_mapping(self):
        self.env.companies._map_eu_taxes()

    @api.depends('company_id')
    def _compute_l10n_eu_oss_european_country(self):
        european_countries = self.env.ref('base.europe').country_ids
        for record in self:
            record.l10n_eu_oss_eu_country = record.company_id.account_fiscal_country_id in european_countries
