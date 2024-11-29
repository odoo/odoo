# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('rw')
    def _get_rw_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'rw_190',
            'property_account_payable_id': 'rw_311',
        }

    @template('rw', 'res.company')
    def _get_rw_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.rw',
                'cash_account_code_prefix': '101',
                'bank_account_code_prefix': '103',
                'transfer_account_code_prefix': '105',
                'account_default_pos_receivable_account_id': 'rw_155',
                'income_currency_exchange_account_id': 'rw_671',
                'expense_currency_exchange_account_id': 'rw_672',
                'deferred_revenue_account_id': 'rw_181',
                'deferred_expense_account_id': 'rw_342',
                'account_sale_tax_id': 'VAT_S_IN_RW_18',
                'account_purchase_tax_id': 'VAT_P_IN_RW_18',
                'expense_account_id': 'rw_510',
                'income_account_id': 'rw_400',
            },
        }
