# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mu')
    def _get_mu_template_data(self):
        return {
            'property_account_receivable_id': 'mu_receivable',
            'property_account_payable_id': 'mu_payable',
            'property_stock_valuation_account_id': 'mu_stock_valuation',
            'property_advance_tax_payment_account_id': 'mu_tax_paid',
            'property_tax_payable_account_id': 'mu_tax_payable',
            'property_tax_receivable_account_id': 'mu_tax_receivable',
            'use_anglo_saxon': False,
            'code_digits': '6',
        }

    @template('mu', 'res.company')
    def _get_mu_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.mu',
                'bank_account_code_prefix': '230',
                'cash_account_code_prefix': '231',
                'transfer_account_code_prefix': '232',
                'account_default_pos_receivable_account_id': 'mu_pos_receivable',
                'income_currency_exchange_account_id': 'mu_income_currency_exchange',
                'expense_currency_exchange_account_id': 'mu_expense_currency_exchange',
                'account_journal_early_pay_discount_gain_account_id': 'mu_cash_discount_gain',
                'account_journal_early_pay_discount_loss_account_id': 'mu_cash_discount_loss',
                'default_cash_difference_income_account_id': 'mu_cash_diff_income',
                'default_cash_difference_expense_account_id': 'mu_cash_diff_expense',
                'account_sale_tax_id': 'mu_tax_sale_15',
                'account_purchase_tax_id': 'mu_tax_purchase_15',
                'expense_account_id': 'mu_expense',
                'income_account_id': 'mu_income',
            },
        }
