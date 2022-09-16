# -*- coding: utf-8 -*-
from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    # Write paperformat and report template used on company
    def _load(self, company):
        res = super(AccountChartTemplate, self)._load(company)
        if self == self.env.ref('l10n_at.l10n_at_chart_template'):
            company.write({
                'external_report_layout_id': self.env.ref('l10n_din5008.external_layout_din5008').id,
                'paperformat_id': self.env.ref('l10n_din5008.paperformat_euro_din').id
            })
        return res

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_at.l10n_at_chart_template'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '5800')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Skontoerträge auf Materialaufwand"),
                'code': 5800,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_at.l10n_at_chart_template'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '8350')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Nicht ausgenützte Lieferantenskonti"),
                'code': 8350,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account
