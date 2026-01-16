# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('th')
    def _get_th_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'l10n_th_account_112100',
            'property_account_payable_id': 'l10n_th_account_212100',
            'property_stock_valuation_account_id': 'l10n_th_account_113100',
            'downpayment_account_id': 'l10n_th_account_212400',
        }

    @template('th', 'res.company')
    def _get_th_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.th',
                'bank_account_code_prefix': '11120',
                'cash_account_code_prefix': '11110',
                'transfer_account_code_prefix': 'l10n_th_account_11120',
                'account_default_pos_receivable_account_id': 'l10n_th_account_112101',
                'income_currency_exchange_account_id': 'l10n_th_account_421300',
                'expense_currency_exchange_account_id': 'l10n_th_account_621200',
                'account_journal_suspense_account_id': 'l10n_th_account_111201',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_th_account_411400',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_th_account_421500',
                'account_sale_tax_id': 'tax_output_vat',
                'account_purchase_tax_id': 'tax_input_vat',
                'default_cash_difference_income_account_id': 'l10n_th_account_421600',
                'default_cash_difference_expense_account_id': 'l10n_th_account_622200',
                'transfer_account_id': 'l10n_th_account_111202',
                'expense_account_id': 'l10n_th_account_511100',
                'income_account_id': 'l10n_th_account_411100',
                'account_stock_valuation_id': 'l10n_th_account_113100',
                'tax_exigibility': 'True'
            },
        }
