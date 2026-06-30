# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('eg')
    def _get_eg_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'egy_account_102011',
            'property_account_payable_id': 'egy_account_201002',
            'property_account_expense_categ_id': 'egy_account_400028',
            'property_account_income_categ_id': 'egy_account_500001',
            }

    @template('eg', 'res.company')
    def _get_eg_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.eg',
                'bank_account_code_prefix': '101',
                'cash_account_code_prefix': '105',
                'transfer_account_code_prefix': '100',
                'account_default_pos_receivable_account_id': 'egy_account_102012',
                'income_currency_exchange_account_id': 'egy_account_500011',
                'expense_currency_exchange_account_id': 'egy_account_400053',
                'account_journal_suspense_account_id': 'egy_account_201001',
                'account_journal_early_pay_discount_loss_account_id': 'egy_account_400079',
                'account_journal_early_pay_discount_gain_account_id': 'egy_account_500014',
                'account_journal_payment_debit_account_id': 'egy_account_101004',
                'account_journal_payment_credit_account_id': 'egy_account_105003',
                'default_cash_difference_income_account_id': 'egy_account_999002',
                'default_cash_difference_expense_account_id': 'egy_account_999001',
                'account_sale_tax_id': 'eg_standard_sale_14',
                'account_purchase_tax_id': 'eg_standard_purchase_14',
            },
        }

    @template('eg', 'account.journal')
    def _get_eg_account_journal(self):
        """ If EGYPT chart, we add 2 new journals TA and IFRS"""
        return {
            "tax_adjustment": {
                "name": "Tax Adjustments",
                "code": "TA",
                "type": "general",
                "sequence": 1,
                "show_on_dashboard": True,
            },
            "ifrs": {
                "name": "IFRS 16",
                "code": "IFRS",
                "type": "general",
                "show_on_dashboard": True,
                "sequence": 10,
            },
        }
