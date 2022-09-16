# -*- coding: utf-8 -*-

from odoo import api, Command, models, _


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

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_nl.l10nnl_chart_template'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '706500')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Betalingskorting crediteuren"),
                'code': 706500,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_nl.l10nnl_chart_template'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '806500')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Betalingskorting debiteuren"),
                'code': 806500,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account
