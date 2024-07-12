from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        if config.company_id.account_fiscal_country_id.code == 'PT':
            result += ['l10n_pt_tax_exemption_reason']
        return result
