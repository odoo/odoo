# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('sk')
    def _get_sk_template_data(self):
        return {
            'code_digits': '6',
            'use_storno_accounting': True,
            'property_account_receivable_id': 'chart_sk_311000',
            'property_account_payable_id': 'chart_sk_321000',
            'property_stock_valuation_account_id': 'chart_sk_132000',
        }

    @template('sk', 'res.company')
    def _get_sk_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.sk',
                'bank_account_code_prefix': '221',
                'cash_account_code_prefix': '211',
                'transfer_account_code_prefix': '261',
                'income_currency_exchange_account_id': 'chart_sk_663000',
                'expense_currency_exchange_account_id': 'chart_sk_563000',
                'account_journal_suspense_account_id': 'chart_sk_261000',
                'account_journal_early_pay_discount_loss_account_id': 'chart_sk_546000',
                'account_journal_early_pay_discount_gain_account_id': 'chart_sk_646000',
                'default_cash_difference_income_account_id': 'chart_sk_668000',
                'default_cash_difference_expense_account_id': 'chart_sk_568000',
                'account_sale_tax_id': 'vy_tuz_23',
                'account_purchase_tax_id': 'vs_tuz_23',
                'expense_account_id': 'chart_sk_504000',
                'income_account_id': 'chart_sk_604000',
            },
        }
