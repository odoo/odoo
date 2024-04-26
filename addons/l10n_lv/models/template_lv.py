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
            'code_digits': '4',
        }

    @template('lv', 'res.company')
    def _get_lv_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.lv',
                'bank_account_code_prefix': '2620',
                'cash_account_code_prefix': '2610',
                'transfer_account_code_prefix': '2700',
                'account_default_pos_receivable_account_id': 'a2613',
                'income_currency_exchange_account_id': 'a8150',
                'expense_currency_exchange_account_id': 'a8250',
                'account_journal_suspense_account_id': 'a26291',
                'account_journal_early_pay_discount_loss_account_id': 'a8299',
                'account_journal_early_pay_discount_gain_account_id': 'a8199',
                'default_cash_difference_income_account_id': 'a8199',
                'default_cash_difference_expense_account_id': 'a8299',
                'account_sale_tax_id': 'VAT_S_G_21_LV',
                'account_purchase_tax_id': 'VAT_P_G_21_LV',
                'expense_account_id': 'a7550',
                'income_account_id': 'a6110',
            },
        }
