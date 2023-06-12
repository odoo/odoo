# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('dz')
    def _get_dz_template_data(self):
        return {
            'property_account_receivable_id': 'dz_pcg_recv',
            'property_account_payable_id': 'dz_pcg_pay',
            'property_account_expense_categ_id': 'pcg_6001',
            'property_account_income_categ_id': 'pcg_7001',
            'code_digits': 6,
            'display_invoice_amount_total_words': True,
        }

    @template('dz', 'res.company')
    def _get_dz_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.dz',
                'bank_account_code_prefix': '512',
                'cash_account_code_prefix': '53',
                'transfer_account_code_prefix': '58',
                'account_default_pos_receivable_account_id': 'dz_pcg_recv_pos',
                'income_currency_exchange_account_id': 'pcg_766',
                'expense_currency_exchange_account_id': 'pcg_666',
            },
        }
