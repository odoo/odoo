# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('me')
    def _get_me_template_data(self):
        return {
            'name': self.env._("Montenegrin Chart of Accounts"),
            'code_digits': '6',
        }

    @template('me', 'res.company')
    def _get_me_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.me',
                'anglo_saxon_accounting': True,
                'tax_exigibility': True,
                'bank_account_code_prefix': '241',
                'cash_account_code_prefix': '243',
                'transfer_account_code_prefix': '247',
                'account_sale_tax_id': 'me_tax_sale_21_g',
                'account_purchase_tax_id': 'me_tax_purchase_21_g',
                'income_account_id': 'me_account_602000',
                'expense_account_id': 'me_account_501000',
                'receivable_account_id': 'me_account_202000',
                'payable_account_id': 'me_account_433000',
                'account_default_pos_receivable_account_id': 'me_account_202100',
                'income_currency_exchange_account_id': 'me_account_663000',
                'expense_currency_exchange_account_id': 'me_account_563000',
                'account_journal_early_pay_discount_gain_account_id': 'me_account_669000',
                'account_journal_early_pay_discount_loss_account_id': 'me_account_569000',
                'default_cash_difference_income_account_id': 'me_account_679000',
                'default_cash_difference_expense_account_id': 'me_account_579000',
                'account_stock_valuation_id': 'me_account_131000',
                'deferred_expense_account_id': 'me_account_280000',
                'deferred_revenue_account_id': 'me_account_491000',
            },
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'me' and code_prefix in ('241', '243', '247'):
            return 'me_account_group_24'
        return super()._get_account_parent_xmlid(code_prefix, template_code)
