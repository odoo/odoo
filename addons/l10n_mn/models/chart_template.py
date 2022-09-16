# coding: utf-8
from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_mn.mn_chart_1'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '99900003')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Cash Discount Loss"),
                'code': 99900003,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_mn.mn_chart_1'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '99900004')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Cash Discount Gain"),
                'code': 99900004,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account
