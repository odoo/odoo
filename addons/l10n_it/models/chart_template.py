# coding: utf-8
from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_it.l10n_it_chart_template_generic'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '411100')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Ribassi e abbuoni attivi"),
                'code': 411100,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_it.l10n_it_chart_template_generic'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '311100')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Discounts and allowances"),
                'code': 311100,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_loss_account
