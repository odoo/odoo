# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('rs')
    def _get_rs_template_data(self):
        return {
            'property_account_payable_id': 'rs_435',
            'property_account_receivable_id': 'rs_204',
            'code_digits': '4',
            'use_storno_accounting': True,
        }

    @template('rs', 'res.company')
    def _get_rs_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.rs',
                'bank_account_code_prefix': '241',
                'cash_account_code_prefix': '243',
                'transfer_account_code_prefix': '250',
                'income_currency_exchange_account_id': 'rs_663',
                'expense_currency_exchange_account_id': 'rs_563',
                'default_cash_difference_income_account_id': 'rs_6791',
                'default_cash_difference_expense_account_id': 'rs_5791',
                'account_sale_tax_id': 'rs_sale_vat_20',
                'account_purchase_tax_id': 'rs_purchase_vat_20',
                'expense_account_id': 'rs_501',
                'income_account_id': 'rs_604',
            },
        }
