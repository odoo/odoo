# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ma')
    def _get_ma_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'pcg_34211',
            'property_account_payable_id': 'pcg_44111',
            'property_account_income_categ_id': 'pcg_7111',
            'property_account_expense_categ_id': 'pcg_6111',
            'display_invoice_amount_total_words': True,
        }

    @template('ma', 'res.company')
    def _get_ma_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ma',
                'bank_account_code_prefix': '5141',
                'cash_account_code_prefix': '51611',
                'transfer_account_code_prefix': '5115',
                'account_default_pos_receivable_account_id': 'pcg_34218',
                'income_currency_exchange_account_id': 'pcg_7331',
                'expense_currency_exchange_account_id': 'pcg_6331',
                'account_journal_suspense_account_id': 'pcg_3497',
                'default_cash_difference_income_account_id': 'pcg_73861',
                'default_cash_difference_expense_account_id': 'pcg_63861',
                'account_journal_early_pay_discount_gain_account_id': 'pcg_73862',
                'account_journal_early_pay_discount_loss_account_id': 'pcg_63862',
                'account_sale_tax_id': 'vat_out_20_80',
                'account_purchase_tax_id': 'vat_in_20_146',
            },
        }
