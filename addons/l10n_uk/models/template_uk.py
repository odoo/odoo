# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('uk')
    def _get_uk_template_data(self):
        return {
            'property_account_receivable_id': '1100',
            'property_account_payable_id': '2100',
            'property_account_expense_categ_id': '5000',
            'property_account_income_categ_id': '4000',
            'property_tax_payable_account_id': '2202',
            'property_tax_receivable_account_id': '2202',
            'code_digits': '6',
        }

    @template('uk', 'res.company')
    def _get_uk_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.uk',
                'bank_account_code_prefix': '1200',
                'cash_account_code_prefix': '1210',
                'transfer_account_code_prefix': '1220',
                'account_default_pos_receivable_account_id': '1104',
                'income_currency_exchange_account_id': '7700',
                'expense_currency_exchange_account_id': '7700',
                'account_sale_tax_id': 'ST11',
                'account_purchase_tax_id': 'PT11',
            },
        }
