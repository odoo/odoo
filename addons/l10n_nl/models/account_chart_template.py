# -*- coding: utf-8 -*-

from odoo import api, Command, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        # Add tag to 999999 account
        res = super(AccountChartTemplate, self)._load(company)
        if company.account_fiscal_country_id.code == 'NL':
            account = self.env['account.account'].search([('code', '=', '999999'), ('company_id', '=', self.env.company.id)])
            if account:
                account.tag_ids = [(4, self.env.ref('l10n_nl.account_tag_12').id)]
        return res

    @api.model
    def _create_liquidity_journal_suspense_account(self, company, code_digits):
        account = super()._create_liquidity_journal_suspense_account(company, code_digits)
        if company.account_fiscal_country_id.code == 'NL':
            account.tag_ids = [Command.link(self.env.ref('l10n_nl.account_tag_25').id)]
        return account
