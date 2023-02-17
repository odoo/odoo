# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ec')
    def _get_ec_template_data(self):
        return {
            'property_account_receivable_id': 'ec1102050101',
            'property_account_payable_id': 'ec210301',
            'property_account_expense_categ_id': 'ec110307',
            'property_account_income_categ_id': 'ec410201',
            'property_account_expense_id': 'ec52040201',
            'property_stock_account_input_categ_id': 'ec110307',
            'property_stock_account_output_categ_id': 'ec510102',
            'property_stock_valuation_account_id': 'ec110306',
            'code_digits': '4',
        }

    @template('ec', 'res.company')
    def _get_ec_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ec',
                'bank_account_code_prefix': '1101020',
                'cash_account_code_prefix': '1101010',
                'transfer_account_code_prefix': '1101030',
                'account_default_pos_receivable_account_id': 'ec1102050101',
                'income_currency_exchange_account_id': 'ec430501',
                'expense_currency_exchange_account_id': 'ec520304',
                'account_journal_early_pay_discount_loss_account_id': 'ec9993',
                'account_journal_early_pay_discount_gain_account_id': 'ec9994',
            },
        }
