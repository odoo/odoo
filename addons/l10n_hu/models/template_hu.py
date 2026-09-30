# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hu')
    def _get_hu_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_hu_311',
            'property_account_payable_id': 'l10n_hu_454',
            'code_digits': '6',
        }

    @template('hu', 'res.company')
    def _get_hu_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.hu',
                'bank_account_code_prefix': '384',
                'cash_account_code_prefix': '381',
                'transfer_account_code_prefix': '389',
                'income_currency_exchange_account_id': 'l10n_hu_976',
                'expense_currency_exchange_account_id': 'l10n_hu_876',
                'account_sale_tax_id': 'F27',
                'account_purchase_tax_id': 'V27',
                'expense_account_id': 'l10n_hu_811',
                'income_account_id': 'l10n_hu_911',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'l10n_hu_211',
            },
        }

    @template('hu', 'account.account')
    def _get_hu_account_account(self):
        return {
            'l10n_hu_211': {
                'account_stock_expense_id': 'l10n_hu_5111',
                'account_stock_variation_id': 'l10n_hu_581',
            },
        }
