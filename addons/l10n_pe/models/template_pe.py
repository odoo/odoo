# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pe')
    def _get_pe_template_data(self):
        return {
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
                'account_discount_expense_allocation_id': 'chart7411',
                'account_discount_income_allocation_id': 'chart7311',
                'account_sale_tax_id': 'sale_tax_igv_18',
                'account_purchase_tax_id': 'purchase_tax_igv_18',
                'deferred_expense_account_id': 'chart189',
                'deferred_revenue_account_id': 'chart496',
                'expense_account_id': 'chart6011',
                'income_account_id': 'chart70121',
                'receivable_account_id': 'chart1213',
                'payable_account_id': 'chart4212',
                'downpayment_account_id': 'chart496',
                'account_stock_valuation_id': 'chart20111',
                'account_production_wip_account_id': 'chart23111',
                'account_production_wip_overhead_account_id': 'chart23113',
            },
        }

    @template('pe', 'account.journal')
    def _get_pe_account_journal(self):
        return {
            'purchase': {
                'default_account_id': 'chart6011',
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
