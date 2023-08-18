# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        """ Set tax calculation rounding method required in Italian localization
        Also to avoid rounding errors when sent with FatturaPA"""
        res = super()._load(company)
        if company.account_fiscal_country_id.code == 'IT':
            company.write({'tax_calculation_rounding_method': 'round_globally'})
            vat_split_payment_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '2607%')])
            split_payment_tax_group = self.env.ref('l10n_it.tax_group_split_payment').with_company(company)
            split_payment_tax_group.property_tax_receivable_account_id = vat_split_payment_account
            split_payment_tax_group.property_tax_payable_account_id = vat_split_payment_account
        return res
