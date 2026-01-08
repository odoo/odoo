# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pl')
    def _get_pl_template_data(self):
        return {
            'property_account_receivable_id': 'chart20000100',
            'property_account_payable_id': 'chart21000100',
            'property_account_expense_categ_id': 'chart70010100',
            'property_account_income_categ_id': 'chart73000100',
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
                'account_default_pos_receivable_account_id': 'chart20000200',
                'income_currency_exchange_account_id': 'chart75000600',
                'expense_currency_exchange_account_id': 'chart75010400',
                'account_journal_early_pay_discount_loss_account_id': 'chart75010900',
                'account_journal_early_pay_discount_gain_account_id': 'chart75000900',
                'default_cash_difference_income_account_id': 'chart75000700',
                'default_cash_difference_expense_account_id': 'chart75010500',
            },
        }
