# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('syscebnl')
    def _get_syscebnl_template_data(self):
        return {
            'property_account_receivable_id': 'syscebnl_409',
            'property_account_payable_id': 'syscebnl_419',
            'name': 'SYSCEBNL',
            'code_digits': '6',
        }

    @template('syscebnl', 'res.company')
    def _get_syscebnl_res_company(self):
        return {
            self.env.company.id: {
                'bank_account_code_prefix': '521',
                'cash_account_code_prefix': '571',
                'transfer_account_code_prefix': '585',
                'account_default_pos_receivable_account_id': 'syscebnl_412',
                'income_currency_exchange_account_id': 'syscebnl_776',
                'expense_currency_exchange_account_id': 'syscebnl_676',
                'account_journal_early_pay_discount_loss_account_id': 'syscebnl_601',
                'account_journal_early_pay_discount_gain_account_id': 'syscebnl_773',
                'default_cash_difference_expense_account_id': 'syscebnl_658',
                'default_cash_difference_income_account_id': 'syscebnl_758',
                'expense_account_id': 'syscebnl_601',
                'income_account_id': 'syscebnl_7051',
            },
        }
