# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        if config.company_id.account_fiscal_country_id.code == 'TW':
            result += ['l10n_tw_edi_tax_type']
        return result
