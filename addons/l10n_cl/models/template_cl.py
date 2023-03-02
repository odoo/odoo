# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cl')
    def _get_cl_template_data(self):
        return {
            'code_digits': '6',
            'use_anglo_saxon': True,
            'property_account_receivable_id': 'account_110310',
            'property_account_payable_id': 'account_210210',
            'property_account_expense_categ_id': 'account_410235',
            'property_account_income_categ_id': 'account_310115',
            'property_stock_account_input_categ_id': 'account_210230',
            'property_stock_account_output_categ_id': 'account_110640',
            'property_stock_valuation_account_id': 'account_110610',
        }

    @template('cl', 'res.company')
    def _get_cl_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cl',
                'bank_account_code_prefix': '1101',
                'cash_account_code_prefix': '1101',
                'transfer_account_code_prefix': '117',
                'account_default_pos_receivable_account_id': 'account_110421',
                'income_currency_exchange_account_id': 'account_410195',
                'expense_currency_exchange_account_id': 'account_410195',
                'tax_calculation_rounding_method': 'round_globally',
            },
        }
