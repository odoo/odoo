# coding: utf-8
from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_hk.l10n_hk_chart_template'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '525000')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Cash Discount Loss"),
                'code': 525000,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_hk.l10n_hk_chart_template'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '425000')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Cash Discount Gain"),
                'code': 425000,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account
