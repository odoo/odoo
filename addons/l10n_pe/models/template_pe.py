# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pe')
    def _get_pe_template_data(self):
        return {
            'property_account_receivable_id': 'chart1213',
            'property_account_payable_id': 'chart4212',
            'property_account_expense_categ_id': 'chart6329',
            'property_account_expense_id': 'chart6011',
            'property_account_income_categ_id': 'chart70121',
            'property_stock_account_input_categ_id': 'chart6111',
            'property_stock_account_output_categ_id': 'chart69111',
            'property_stock_valuation_account_id': 'chart20111',
            'code_digits': '7',
        }

    @template('pe', 'res.company')
    def _get_pe_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.pe',
                'bank_account_code_prefix': '1041',
                'cash_account_code_prefix': '1031',
                'transfer_account_code_prefix': '1051',
                'account_default_pos_receivable_account_id': 'chart1215',
                'income_currency_exchange_account_id': 'chart776',
                'expense_currency_exchange_account_id': 'chart676',
                'account_journal_early_pay_discount_loss_account_id': 'chart675',
                'account_journal_early_pay_discount_gain_account_id': 'chart775',
            },
        }
