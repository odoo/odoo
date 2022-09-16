# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        journal_data = super(AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict)
        for journal in journal_data:
            if journal['type'] in ('sale', 'purchase') and company.country_id.code == "BE":
                journal.update({'refund_sequence': True})
        return journal_data

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_be.l10nbe_chart_template'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '653000')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Amount of the discount borne by the enterprise, as a result of negotiating amounts receivable"),
                'code': 653000,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_be.l10nbe_chart_template'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '757000')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Discounts Taken"),
                'code': 757000,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account
