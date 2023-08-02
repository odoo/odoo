# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('lv')
    def _get_lv_template_data(self):
        return {
            'property_account_receivable_id': 'a2310',
            'property_account_payable_id': 'a5310',
            'property_account_expense_categ_id': 'a7550',
            'property_account_income_categ_id': 'a6110',
            'code_digits': '4',
            'use_anglo_saxon': True,
        }

    @template('lv', 'res.company')
    def _get_lv_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.lv',
                'bank_account_code_prefix': '2620',
                'cash_account_code_prefix': '2610',
                'transfer_account_code_prefix': '2699',
                'account_default_pos_receivable_account_id': 'a2613',
                'income_currency_exchange_account_id': 'a8150',
                'expense_currency_exchange_account_id': 'a8250',
                'account_journal_suspense_account_id': 'a26291',
                'account_journal_early_pay_discount_loss_account_id': 'a8299',
                'account_journal_early_pay_discount_gain_account_id': 'a8199',
                'account_journal_payment_debit_account_id': 'a26292',
                'account_journal_payment_credit_account_id': 'a26293',
                'default_cash_difference_income_account_id': 'a8199',
                'default_cash_difference_expense_account_id': 'a8299',
                'account_sale_tax_id': 'tax_sale_vat_21',
                'account_purchase_tax_id': 'tax_purchase_vat_21',
            },
        }
