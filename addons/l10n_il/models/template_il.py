# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('il')
    def _get_il_template_data(self):
        return {
            'property_account_receivable_id': 'il_account_101200',
            'property_account_payable_id': 'il_account_111100',
            'property_account_expense_categ_id': 'il_account_212200',
            'property_account_income_categ_id': 'il_account_200000',
            'property_stock_account_input_categ_id': 'il_account_101120',
            'property_stock_account_output_categ_id': 'il_account_101130',
            'property_stock_valuation_account_id': 'il_account_101110',
            'code_digits': '6',
        }

    @template('il', 'res.company')
    def _get_il_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.il',
                'bank_account_code_prefix': '1014',
                'cash_account_code_prefix': '1015',
                'transfer_account_code_prefix': '1017',
                'account_default_pos_receivable_account_id': 'il_account_101201',
                'income_currency_exchange_account_id': 'il_account_201000',
                'expense_currency_exchange_account_id': 'il_account_202100',
            },
        }
