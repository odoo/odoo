from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _prepare_liquidity_account_vals(self, company, code, vals):
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)
        if company.account_fiscal_country_id.code == 'PT':
            if vals.get('type') == 'cash':
                account_vals['l10n_pt_taxonomy_code'] = 1
            elif vals.get('type') == 'bank':
                account_vals['l10n_pt_taxonomy_code'] = 2
        return account_vals
