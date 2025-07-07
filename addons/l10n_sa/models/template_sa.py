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
                'income_currency_exchange_account_id': 'sa_account_500011',
                'expense_currency_exchange_account_id': 'sa_account_400053',
                'account_sale_tax_id': 'sa_sales_tax_15',
                'account_purchase_tax_id': 'sa_purchase_tax_15',
                'expense_account_id': 'sa_account_400001',
                'income_account_id': 'sa_account_500001',
                'deferred_expense_account_id': 'sa_account_104020',
                'deferred_revenue_account_id': 'sa_account_201018',
                'account_cash_basis_base_account_id': 'sa_account_201030',
            },
        }

    @template('sa', 'account.journal')
    def _get_sa_account_journal(self):
        """ If Saudi Arabia chart, we add 3 new journals Tax Adjustments, IFRS 16 and Zakat"""
        return {
            "tax_adjustment": {
                'name': 'Tax Adjustments',
                'code': 'TA',
                'type': 'general',
                'show_on_dashboard': True,
                'sequence': 1,
            },
            "ifrs16": {
                'name': 'IFRS 16 Right of Use Asset',
                'code': 'IFRS',
                'type': 'general',
                'show_on_dashboard': True,
                'sequence': 10,
            },
            "zakat": {
                'name': 'Zakat',
                'code': 'ZAKAT',
                'type': 'general',
                'show_on_dashboard': True,
                'sequence': 10,
            }
        }
