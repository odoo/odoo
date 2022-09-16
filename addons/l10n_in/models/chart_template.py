# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        res = super(AccountChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        if self == self.env.ref('l10n_in.indian_chart_template_standard'):
            for journal in res:
                if journal.get('type') in ('sale','purchase'):
                    journal['l10n_in_gstin_partner_id'] = company.partner_id.id
                if journal['code'] == 'INV':
                    journal['name'] = _('Tax Invoices')
        return res

    def _load(self, company):
        res = super(AccountChartTemplate, self)._load(company)
        if self == self.env.ref("l10n_in.indian_chart_template_standard"):
            company.write({'fiscalyear_last_month': '3'})
        return res

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_in.indian_chart_template_standard'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '213200')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Write Off Expense"),
                'code': 213200,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_in.indian_chart_template_standard'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '201200')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Write off Income"),
                'code': 201200,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account

class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    l10n_in_reverse_charge = fields.Boolean("Reverse charge", help="Tick this if this tax is reverse charge. Only for Indian accounting")
    
    def _get_tax_vals(self, company, tax_template_to_tax):
        val = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        if self.tax_group_id:
            val['l10n_in_reverse_charge'] = self.l10n_in_reverse_charge
        return val
