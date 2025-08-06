from odoo import api, models, Command


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        # OVERRIDE
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)

        if company.account_fiscal_country_id.code == 'IE':
            # Ensure the newly created liquidity accounts have the right account tag in order to be part
            # of the Irish BS and PL tags reports.
            account_vals.setdefault('tag_ids', [])
            account_vals['tag_ids'] += [
                Command.link(self.env.ref('l10n_ie.l10n_ie_account_tag_cash_bank_hand').id),
            ]

        return account_vals
