# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ve')
    def _get_ve_template_data(self):
        return {
            'code_digits': '7',
            'property_account_receivable_id': 'account_account_1101010',
            'property_account_payable_id': 'account_account_2101010',
            'property_account_expense_categ_id': 'account_account_5101010',
            'property_account_income_categ_id': 'account_account_4101010',
        }

    @template('ve', 'res.company')
    def _get_ve_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ve',
                'bank_account_code_prefix': '1014',
                'cash_account_code_prefix': '1015',
                'transfer_account_code_prefix': '1013',
                'transfer_account_id': 'account_account_1013010',
                'account_default_pos_receivable_account_id': 'account_account_1101020',
                'income_currency_exchange_account_id': 'account_account_4301010',
                'expense_currency_exchange_account_id': 'account_account_6501040',
                'account_journal_suspense_account_id': 'account_account_1012010',
                'account_journal_payment_debit_account_id': 'account_account_1012020',
                'account_journal_payment_credit_account_id': 'account_account_1012030',
                'account_journal_early_pay_discount_gain_account_id': 'account_account_4301040',
                'account_journal_early_pay_discount_loss_account_id': 'account_account_6501060',
                'default_cash_difference_income_account_id': 'account_account_4301030',
                'default_cash_difference_expense_account_id': 'account_account_6501050',
                'account_sale_tax_id': 'tax1sale',
                'account_purchase_tax_id': 'tax1purchase',
            },
        }
