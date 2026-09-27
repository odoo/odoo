from odoo import api, models, Command


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        ''' Set tags on new bank and cash accounts.'''
        # OVERRIDE
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)

        if company.account_fiscal_country_id.code == 'LT':
            account_vals.setdefault('tag_ids', [])
            account_vals['tag_ids'] += [
                Command.link(self.env.ref('l10n_lt.account_account_tag_b_4').id),
            ]

        return account_vals
