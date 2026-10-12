# -*- coding: utf-8 -*-

from odoo import api, models, Command


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        ''' Set Balance Sheet and SAF-T tags on new bank and cash accounts.'''
        # OVERRIDE
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)

        if company.account_fiscal_country_id.code == 'AT':
            account_vals.setdefault('tag_ids', [])
            account_vals['tag_ids'] += [
                Command.link(self.env.ref('l10n_at.account_tag_l10n_at_ABIV').id),
                Command.link(self.env.ref('l10n_at.account_tag_external_code_2300').id),
            ]

        return account_vals
