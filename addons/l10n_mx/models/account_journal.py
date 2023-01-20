# -*- coding: utf-8 -*-

from odoo import models, api, Command


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def _prepare_liquidity_account_vals(self, company, code, vals):
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)
        if company.account_fiscal_country_id.code != 'MX':
            return account_vals
        # Ensure Cash account has the correct tags in order to export the COA
        account_vals.setdefault('tag_ids', []).append(Command.link(self.env.ref('l10n_mx.tag_credit_balance_account').id))
        return account_vals
