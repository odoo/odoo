# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ve')
    def _get_ve_template_data(self):
        return {
            'code_digits': '7',
            'property_account_receivable_id': 'account_account_1106001',
            'property_account_payable_id': 'account_account_2101002',
            'property_account_expense_categ_id': 'account_account_5101001',
            'property_account_income_categ_id': 'account_account_4101001',
        }

    @template('ve', 'res.company')
    def _get_ve_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ve',
                'cash_account_code_prefix': '1101',
                'bank_account_code_prefix': '1102',
                'transfer_account_code_prefix': '1129003',
                'account_default_pos_receivable_account_id': 'account_account_1106001',
                'income_currency_exchange_account_id': 'account_account_4102004',
                'expense_currency_exchange_account_id': 'account_account_5102014',
                'tax_calculation_rounding_method': 'round_globally',
                'account_sale_tax_id': 'tax1sale',
                'account_purchase_tax_id': 'tax1purchase',
            },
        }
