# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('tw')
    def _get_tw_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'tw_119100',
            'property_account_payable_id': 'tw_217100',
            'property_stock_valuation_account_id': 'tw_123100',
        }

    @template('tw', 'res.company')
    def _get_tw_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.tw',
                'bank_account_code_prefix': '1113',
                'cash_account_code_prefix': '1111',
                'transfer_account_code_prefix': '1114',
                'account_default_pos_receivable_account_id': 'tw_119150',
                'income_currency_exchange_account_id': 'tw_718100',
                'expense_currency_exchange_account_id': 'tw_718200',
                'account_journal_early_pay_discount_loss_account_id': 'tw_411400',
                'account_journal_early_pay_discount_gain_account_id': 'tw_512400',
                'default_cash_difference_income_account_id': 'tw_718500',
                'default_cash_difference_expense_account_id': 'tw_718600',
                'account_sale_tax_id': 'tw_tax_sale_5',
                'account_purchase_tax_id': 'tw_tax_purchase_5',
                'expense_account_id': 'tw_511100',
                'income_account_id': 'tw_411100',
                'tax_calculation_rounding_method': 'round_globally',
            },
        }
