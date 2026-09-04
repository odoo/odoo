# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ve')
    def _get_ve_template_data(self):
        return {
            'code_digits': '9',
            'property_account_receivable_id': 'account_account_101060101',
            'property_account_payable_id': 'account_account_201010201',
            'property_account_expense_categ_id': 'account_account_501010101',
            'property_account_income_categ_id': 'account_account_401010101',
            'property_stock_valuation_account_id': 'account_account_101050101',
        }

    @template('ve', 'res.company')
    def _get_ve_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ve',
                'cash_account_code_prefix': '10101',
                'bank_account_code_prefix': '10102',
                'transfer_account_code_prefix': '10109',
                'account_default_pos_receivable_account_id': 'account_account_101060101',
                'account_journal_suspense_account_id': 'account_account_199990101',
                'account_journal_payment_debit_account_id': 'account_account_199020101',
                'account_journal_payment_credit_account_id': 'account_account_199010101',
                'default_cash_difference_income_account_id': 'account_account_402010301',
                'income_currency_exchange_account_id': 'account_account_402010401',
                'expense_currency_exchange_account_id': 'account_account_603010101',
                'tax_calculation_rounding_method': 'round_globally',
                'account_sale_tax_id': 'tax1sale',
                'account_purchase_tax_id': 'tax1purchase',
            },
        }
