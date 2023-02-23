# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('kz')
    def _get_kz_template_data(self):
        return {
            'property_account_receivable_id': 'kz1210',
            'property_account_payable_id': 'kz3310',
            'property_account_income_categ_id': 'kz6010',
            'property_account_expense_categ_id': 'kz1330',
            'code_digits': '4',
        }

    @template('kz', 'res.company')
    def _get_kz_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.kz',
                'bank_account_code_prefix': '103',
                'cash_account_code_prefix': '101',
                'transfer_account_code_prefix': '102',
                'income_currency_exchange_account_id': 'kz6250',
                'expense_currency_exchange_account_id': 'kz7430',
                'account_journal_early_pay_discount_loss_account_id': 'kz7481',
                'account_journal_early_pay_discount_gain_account_id': 'kz6291',
                'default_cash_difference_income_account_id': 'kz6210',
                'default_cash_difference_expense_account_id': 'kz7410',
            },
        }
