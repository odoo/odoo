# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pl')
    def _get_pl_template_data(self):
        return {
            'property_account_receivable_id': 'chart20000000',
            'property_account_payable_id': 'chart21000000',
            'property_account_expense_categ_id': 'chart70110000',
            'property_account_income_categ_id': 'chart73010000',
            'code_digits': '8',
            'use_storno_accounting': True,
        }

    @template('pl', 'res.company')
    def _get_pl_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.pl',
                'bank_account_code_prefix': '11.000.00',
                'cash_account_code_prefix': '12.000.00',
                'transfer_account_code_prefix': '11.090.00',
                'account_default_pos_receivable_account_id': 'chart20000100',
                'income_currency_exchange_account_id': 'chart75060000',
                'expense_currency_exchange_account_id': 'chart75140000',
                'account_journal_early_pay_discount_loss_account_id': 'chart75190000',
                'account_journal_early_pay_discount_gain_account_id': 'chart75070000',
                'default_cash_difference_income_account_id': 'chart77000000',
                'default_cash_difference_expense_account_id': 'chart77100000',
            },
        }
