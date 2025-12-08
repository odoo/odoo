# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('vn')
    def _get_vn_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'chart1311',
            'property_account_payable_id': 'chart3311',
            'property_stock_valuation_account_id': 'chart1551',
            'display_invoice_amount_total_words': True,
        }

    @template('vn', 'res.company')
    def _get_vn_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.vn',
                'bank_account_code_prefix': '112',
                'cash_account_code_prefix': '111',
                'transfer_account_code_prefix': '113',
                'account_default_pos_receivable_account_id': 'chart1311',
                'income_currency_exchange_account_id': 'chart515',
                'expense_currency_exchange_account_id': 'chart635',
                'account_journal_early_pay_discount_loss_account_id': 'chart635',
                'account_journal_early_pay_discount_gain_account_id': 'chart515',
                'account_sale_tax_id': 'tax_sale_vat10',
                'account_purchase_tax_id': 'tax_purchase_vat10',
                'transfer_account_id': 'chart1131',
                'expense_account_id': 'chart632',
                'income_account_id': 'chart5111',
                'deferred_expense_account_id': 'chart2421',
                'deferred_revenue_account_id': 'chart33871',
                'account_production_wip_account_id': 'chart154',
                'default_cash_difference_income_account_id': 'chart711',
                'default_cash_difference_expense_account_id': 'chart811',
                'tax_calculation_rounding_method': 'round_per_line',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'chart152',
                'account_journal_suspense_account_id': 'chart1121',
            },
        }

    @template('vn', 'account.account')
    def _get_vn_account_account(self):
        return {
            'chart152': {
                'account_stock_variation_id': 'chart632',
            },
        }

    @template('vn', 'account.journal')
    def _get_vn_account_journal(self):
        return {
            'bank': {'default_account_id': 'chart112'},
            'cash': {
                'name': self.env._("Cash"),
                'type': 'cash',
                'default_account_id': 'chart1111',
            },
        }
