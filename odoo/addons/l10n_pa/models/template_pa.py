# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pa')
    def _get_pa_template_data(self):
        return {
            'code_digits': '7',
            'property_account_receivable_id': '121',
            'property_account_payable_id': '211',
            'property_account_expense_categ_id': '62_01',
            'property_account_income_categ_id': '411_01',
        }

    @template('pa', 'res.company')
    def _get_pa_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.pa',
                'bank_account_code_prefix': '111.',
                'cash_account_code_prefix': '113.',
                'transfer_account_code_prefix': '112.',
                'account_default_pos_receivable_account_id': '121_01',
                'income_currency_exchange_account_id': 'gain81_01',
                'expense_currency_exchange_account_id': 'loss81_01',
                'account_sale_tax_id': 'ITAX_19',
                'account_purchase_tax_id': 'OTAX_19',
            },
        }
