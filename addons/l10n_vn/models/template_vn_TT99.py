# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('vn_TT99')
    def _get_vn_tt99_template_data(self):
        return {
            'name': 'Chart of Accounts - Circular No. 99/2025/TT-BTC',
            'code_digits': '0',
            'property_account_receivable_id': 'chart131',
            'property_account_payable_id': 'chart331',
            'property_account_expense_categ_id': 'chart156',
            'property_account_income_categ_id': 'chart511',
            'display_invoice_amount_total_words': True,
        }

    @template('vn_TT99', 'res.company')
    def _get_vn_tt99_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': False,
                'account_fiscal_country_id': 'base.vn',
                'bank_account_code_prefix': '112',
                'cash_account_code_prefix': '111',
                'transfer_account_code_prefix': '113',
                'account_default_pos_receivable_account_id': 'chart131',
                'income_currency_exchange_account_id': 'chart515',
                'expense_currency_exchange_account_id': 'chart635',
                'account_journal_early_pay_discount_loss_account_id': 'chart635',
                'account_journal_early_pay_discount_gain_account_id': 'chart515',
                'account_sale_tax_id': 'tax_sale_vat10',
                'account_purchase_tax_id': 'tax_purchase_vat10',
            },
        }
