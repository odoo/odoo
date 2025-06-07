# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('nl')
    def _get_nl_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'recv',
            'property_account_payable_id': 'pay',
            'property_account_expense_categ_id': '7001',
            'property_account_income_categ_id': '8001',
            'property_stock_account_input_categ_id': '1450',
            'property_stock_account_output_categ_id': '1250',
            'property_stock_valuation_account_id': '3200',
        }

    @template('nl', 'res.company')
    def _get_nl_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.nl',
                'bank_account_code_prefix': '103',
                'cash_account_code_prefix': '101',
                'transfer_account_code_prefix': '1060',
                'account_default_pos_receivable_account_id': 'recv_pos',
                'income_currency_exchange_account_id': '8920',
                'expense_currency_exchange_account_id': '4920',
                'account_journal_early_pay_discount_loss_account_id': '7065',
                'account_journal_early_pay_discount_gain_account_id': '8065',
                'l10n_nl_rounding_difference_loss_account_id': '4960',
                'l10n_nl_rounding_difference_profit_account_id': '4950',
                'account_sale_tax_id': 'btw_21',
                'account_purchase_tax_id': 'btw_21_buy',
            },
        }
