# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('jp')
    def _get_jp_template_data(self):
        return {
            'code_digits': '7',
            'property_account_receivable_id': 'A11211',
            'property_account_payable_id': 'A21211',
            'property_account_expense_id': 'A21219',
            'property_account_income_id': 'B41001',
            'property_account_expense_categ_id': 'A21219',
            'property_account_income_categ_id': 'B41001',
        }

    @template('jp', 'res.company')
    def _get_jp_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.jp',
                'bank_account_code_prefix': 'A11102',
                'cash_account_code_prefix': 'A11105',
                'transfer_account_code_prefix': 'A11109',
                'account_default_pos_receivable_account_id': 'A11213',
                'income_currency_exchange_account_id': 'B61501',
                'expense_currency_exchange_account_id': 'B62501',
            },
        }
