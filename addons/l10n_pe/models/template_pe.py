# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pe')
    def _get_pe_template_data(self):
        return {
            'property_account_receivable_id': 'chart1213',
            'property_account_payable_id': 'chart4212',
            'property_stock_valuation_account_id': 'chart20111',
            'code_digits': '7',
        }

    @template('pe', 'res.company')
    def _get_pe_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.pe',
                'bank_account_code_prefix': '1041',
                'cash_account_code_prefix': '1031',
                'transfer_account_code_prefix': '1051',
                'account_default_pos_receivable_account_id': 'chart1215',
                'income_currency_exchange_account_id': 'chart776',
                'expense_currency_exchange_account_id': 'chart676',
                'account_journal_early_pay_discount_loss_account_id': 'chart675',
                'account_journal_early_pay_discount_gain_account_id': 'chart775',
                'account_sale_tax_id': 'sale_tax_igv_18',
                'account_purchase_tax_id': 'purchase_tax_igv_18',
                'expense_account_id': 'chart6329',
                'income_account_id': 'chart70121',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'chart20111',
            },
        }

    @template('pe', 'account.account')
    def _get_pe_account_account(self):
        return {
            'chart20111': {
                'account_stock_expense_id': 'chart6111',
                'account_stock_variation_id': 'chart69121',
            },
        }
