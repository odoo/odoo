# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ua_psbo')
    def _get_ua_psbo_template_data(self):
        return {
            'property_account_receivable_id': 'ua_psbp_361',
            'property_account_payable_id': 'ua_psbp_631',
            'property_account_expense_categ_id': 'ua_psbp_901',
            'property_account_income_categ_id': 'ua_psbp_701',
            'property_stock_account_input_categ_id': 'ua_psbp_2812',
            'property_stock_account_output_categ_id': 'ua_psbp_2811',
            'property_stock_valuation_account_id': 'ua_psbp_281',
            'name': 'План рахунків ПСБО',
            'code_digits': '6',
            'use_storno_accounting': True,
            'display_invoice_amount_total_words': True,
        }

    @template('ua_psbo', 'res.company')
    def _get_ua_psbo_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.ua',
                'bank_account_code_prefix': '311',
                'cash_account_code_prefix': '301',
                'transfer_account_code_prefix': '333',
                'account_default_pos_receivable_account_id': 'ua_psbp_366',
                'income_currency_exchange_account_id': 'ua_psbp_711',
                'expense_currency_exchange_account_id': 'ua_psbp_942',
                'account_sale_tax_id': 'sale_tax_template_vat20_psbo',
                'account_purchase_tax_id': 'purchase_tax_template_vat20_psbo',
            },
        }
