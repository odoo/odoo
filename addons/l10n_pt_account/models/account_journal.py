from odoo import models, api


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.depends('company_id.account_fiscal_country_id.code', 'type')
    def _compute_restrict_mode_hash_table(self):
        super()._compute_restrict_mode_hash_table()
        for journal in self:
            if journal.company_id.account_fiscal_country_id.code == 'PT' and journal.type == 'sale':
                journal.restrict_mode_hash_table = True

    def _prepare_liquidity_account_vals(self, company, code, vals):
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)
        if company.account_fiscal_country_id.code == 'PT':
            if vals.get('type') == 'cash':
                account_vals['l10n_pt_taxonomy_code'] = 1
            elif vals.get('type') == 'bank':
                account_vals['l10n_pt_taxonomy_code'] = 2
        return account_vals
