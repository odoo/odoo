# coding: utf-8
from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if self not in [self.env.ref('l10n_es.account_chart_template_pymes'),
                        self.env.ref('l10n_es.account_chart_template_common'),
                        self.env.ref('l10n_es.account_chart_template_assoc'),
                        self.env.ref('l10n_es.account_chart_template_full')]:
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '606000')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Descuentos sobre compras por pronto pago de mercaderías"),
                'code': 606000,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if self not in [self.env.ref('l10n_es.account_chart_template_pymes'),
                        self.env.ref('l10n_es.account_chart_template_common'),
                        self.env.ref('l10n_es.account_chart_template_assoc'),
                        self.env.ref('l10n_es.account_chart_template_full')]:
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '706000')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Descuentos sobre ventas por pronto pago de mercaderías"),
                'code': 706000,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account
