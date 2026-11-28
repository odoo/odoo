# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('is')
    def _get_is_template_data(self):
        return {
            'code_digits': '4',
        }

    @template('is', 'res.company')
    def _get_is_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.is',
                'bank_account_code_prefix': '320',
                'cash_account_code_prefix': '325',
                'transfer_account_code_prefix': '329',
                'income_account_id': 'is_account_1000',
                'expense_account_id': 'is_account_2000',
                'receivable_account_id': 'is_account_3400',
                'payable_account_id': 'is_account_4200',
                'account_default_pos_receivable_account_id': 'is_account_3410',
                'account_stock_valuation_id': 'is_account_3500',
                'deferred_expense_account_id': 'is_account_3440',
                'deferred_revenue_account_id': 'is_account_4220',
                'income_currency_exchange_account_id': 'is_account_1810',
                'expense_currency_exchange_account_id': 'is_account_2810',
                'account_journal_early_pay_discount_gain_account_id': 'is_account_1830',
                'account_journal_early_pay_discount_loss_account_id': 'is_account_2820',
                'default_cash_difference_income_account_id': 'is_account_1840',
                'default_cash_difference_expense_account_id': 'is_account_2840',
                'account_sale_tax_id': 'is_vat_sale_24',
                'account_purchase_tax_id': 'is_vat_purchase_24',
            },
        }
