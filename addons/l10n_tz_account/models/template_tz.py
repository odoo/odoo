# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('tz')
    def _get_tz_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'tz_190',
            'property_account_payable_id': 'tz_311',
            'property_account_expense_categ_id': 'tz_510',
            'property_account_income_categ_id': 'tz_400',
        }

    @template('tz', 'res.company')
    def _get_tz_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.tz',
                'cash_account_code_prefix': '101',
                'bank_account_code_prefix': '103',
                'transfer_account_code_prefix': '105',
                'account_default_pos_receivable_account_id': 'tz_155',
                'income_currency_exchange_account_id': 'tz_671',
                'expense_currency_exchange_account_id': 'tz_672',
                'deferred_revenue_account_id': 'tz_181',
                'deferred_expense_account_id': 'tz_342',
                'account_sale_tax_id': 'VAT_S_TAXABLE_18',
                'account_purchase_tax_id': 'VAT_P_TAXABLE_18',
            },
        }
