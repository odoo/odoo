# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cz')
    def _get_cz_template_data(self):
        return {
            'code_digits': '6',
            'use_storno_accounting': True,
            'property_account_receivable_id': 'chart_cz_311000',
            'property_account_payable_id': 'chart_cz_321000',
            'property_stock_valuation_account_id': 'chart_cz_132000',
        }

    @template('cz', 'res.company')
    def _get_cz_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cz',
                'bank_account_code_prefix': '221',
                'cash_account_code_prefix': '211',
                'transfer_account_code_prefix': '261',
                'income_currency_exchange_account_id': 'chart_cz_663000',
                'expense_currency_exchange_account_id': 'chart_cz_563000',
                'account_journal_suspense_account_id': 'chart_cz_261000',
                'default_cash_difference_income_account_id': 'chart_cz_668000',
                'default_cash_difference_expense_account_id': 'chart_cz_568000',
                'account_default_pos_receivable_account_id': 'chart_cz_311001',
                'account_sale_tax_id': 'l10n_cz_21_domestic_supplies',
                'account_purchase_tax_id': 'l10n_cz_21_receipt_domestic_supplies',
                'expense_account_id': 'chart_cz_504000',
                'income_account_id': 'chart_cz_604000',
            },
        }
