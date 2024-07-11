# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ve')
    def _get_ve_template_data(self):
        return {
            'code_digits': '7',
            'property_account_receivable_id': 'account_activa_account_1122001',
            'property_account_payable_id': 'account_activa_account_2122001',
            'property_account_expense_categ_id': 'account_activa_account_7151001',
            'property_account_income_categ_id': 'account_activa_account_5111001',
        }

    @template('ve', 'res.company')
    def _get_ve_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ve',
                'bank_account_code_prefix': '1113',
                'cash_account_code_prefix': '1111',
                'transfer_account_code_prefix': '1129003',
                'account_default_pos_receivable_account_id': 'account_activa_account_1122003',
                'income_currency_exchange_account_id': 'account_activa_account_9212003',
                'expense_currency_exchange_account_id': 'account_activa_account_9113006',
                'account_sale_tax_id': 'tax3sale',
                'account_purchase_tax_id': 'tax3purchase',
            },
        }
