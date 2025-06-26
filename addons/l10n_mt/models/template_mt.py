# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mt')
    def _get_mt_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'mt_2050',
            'property_account_payable_id': 'mt_3100',
            'property_account_expense_categ_id': 'mt_5550',
            'property_account_income_categ_id': 'mt_5000',
        }

    @template('mt', 'res.company')
    def _get_mt_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.mt',
                'bank_account_code_prefix': '2150',
                'cash_account_code_prefix': '2155',
                'transfer_account_code_prefix': '2300',
                'account_default_pos_receivable_account_id': 'mt_2040',
                'income_currency_exchange_account_id': 'mt_5400',
                'expense_currency_exchange_account_id': 'mt_5540',
                'account_sale_tax_id': 'VAT_S_IN_MT_18_G',
                'account_purchase_tax_id': 'VAT_P_IN_MT_18_G',
            },
        }
