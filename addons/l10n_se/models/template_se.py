# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('se')
    def _get_se_template_data(self):
        return {
            'property_account_receivable_id': 'a1510',
            'property_account_payable_id': 'a2440',
            'property_account_expense_categ_id': 'a4000',
            'property_account_income_categ_id': 'a3001',
            'property_stock_account_input_categ_id': 'a4960',
            'property_stock_account_output_categ_id': 'a4960',
            'property_stock_valuation_account_id': 'a1410',
            'code_digits': '4',
        }

    @template('se', 'res.company')
    def _get_se_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.se',
                'bank_account_code_prefix': '193',
                'cash_account_code_prefix': '191',
                'transfer_account_code_prefix': '194',
                'account_default_pos_receivable_account_id': 'a1910',
                'income_currency_exchange_account_id': 'a3960',
                'expense_currency_exchange_account_id': 'a3960',
                'account_journal_early_pay_discount_loss_account_id': 'a9993',
                'account_journal_early_pay_discount_gain_account_id': 'a9994',
                'account_sale_tax_id': 'sale_tax_25_goods',
                'account_purchase_tax_id': 'purchase_tax_25_goods',
            },
        }
