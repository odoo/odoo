# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('sa')
    def _get_sa_template_data(self):
        return {
            'property_account_receivable_id': 'sa_account_102011',
            'property_account_payable_id': 'sa_account_201002',
            'property_account_expense_categ_id': 'sa_account_400001',
            'property_account_income_categ_id': 'sa_account_500001',
            'code_digits': '6',
        }

    @template('sa', 'res.company')
    def _get_sa_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.sa',
                'bank_account_code_prefix': '101',
                'cash_account_code_prefix': '105',
                'transfer_account_code_prefix': '100',
                'account_default_pos_receivable_account_id': 'sa_account_102012',
                'income_currency_exchange_account_id': 'sa_account_400053',
                'expense_currency_exchange_account_id': 'sa_account_500011',
            },
        }
