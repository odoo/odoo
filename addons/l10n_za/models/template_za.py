# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('za')
    def _get_za_template_data(self):
        return {
            'property_account_receivable_id': '110010',
            'property_account_payable_id': '220010',
            'property_account_expense_categ_id': '600010',
            'property_account_income_categ_id': '500010',
            'property_stock_account_input_categ_id': '200010',
            'property_stock_account_output_categ_id': '100050',
            'property_stock_valuation_account_id': '100020',
            'use_anglo_saxon': True,
            'code_digits': '6',
        }

    @template('za', 'res.company')
    def _get_za_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.za',
                'bank_account_code_prefix': '1200',
                'cash_account_code_prefix': '1250',
                'transfer_account_code_prefix': '1010',
                'account_default_pos_receivable_account_id': '110030',
                'income_currency_exchange_account_id': '500100',
                'expense_currency_exchange_account_id': '610340',
                'default_cash_difference_income_account_id': '500110',
                'default_cash_difference_expense_account_id': '610460',
                'account_sale_tax_id': 'ST1',
                'account_purchase_tax_id': 'PT15',
            },
        }
