# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ua_ias')
    def _get_ua_ias_template_data(self):
        return {
            'property_account_receivable_id': 'ua_ias_1120',
            'property_account_payable_id': 'ua_ias_1200',
            'property_account_expense_categ_id': 'ua_ias_2200',
            'property_account_income_categ_id': 'ua_ias_2000',
            'property_stock_account_input_categ_id': 'ua_ias_1201',
            'property_stock_account_output_categ_id': 'ua_ias_1121',
            'property_stock_valuation_account_id': 'ua_ias_1100',
            'name': 'План рахунків МСФЗ',
            'code_digits': '6',
            'use_storno_accounting': True,
            'display_invoice_amount_total_words': True,
        }

    @template('ua_ias', 'res.company')
    def _get_ua_ias_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.ua',
                'bank_account_code_prefix': '1112',
                'cash_account_code_prefix': '1111',
                'transfer_account_code_prefix': '1119',
                'account_default_pos_receivable_account_id': 'ua_ias_1122',
                'income_currency_exchange_account_id': 'ua_ias_2100',
                'expense_currency_exchange_account_id': 'ua_ias_2500',
                'account_sale_tax_id': 'sale_tax_template_vat20',
                'account_purchase_tax_id': 'purchase_tax_template_vat20',
            },
        }
