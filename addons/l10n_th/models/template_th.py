# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('th')
    def _get_th_template_data(self):
        return {
            'property_account_receivable_id': 'a_recv',
            'property_account_payable_id': 'a_pay',
        }

    @template('th', 'res.company')
    def _get_th_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.th',
                'bank_account_code_prefix': '1110',
                'cash_account_code_prefix': '1100',
                'transfer_account_code_prefix': '16',
                'account_default_pos_receivable_account_id': 'a_recv_pos',
                'income_currency_exchange_account_id': 'a_income_gain',
                'expense_currency_exchange_account_id': 'a_exp_loss',
                'account_sale_tax_id': 'tax_output_vat',
                'account_purchase_tax_id': 'tax_input_vat',
                'expense_account_id': 'a_exp_cogs',
                'income_account_id': 'a_sales',
            },
        }
