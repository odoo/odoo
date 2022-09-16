# coding: utf-8
from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_lt.account_chart_template_lithuania'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        return self.env['account.account'].create({
            'name': _("Discounts, Returns (-)"),
            'code': 509,
            'account_type': 'expense',
            'company_id': company.id,
        })

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_lt.account_chart_template_lithuania'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        return self.env['account.account'].create({
            'name': _("Discounts Received (-)"),
            'code': 6209,
            'account_type': 'income_other',
            'company_id': company.id,
        })
