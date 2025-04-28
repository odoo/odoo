# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ph')
    def _get_ph_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_ph_account_110000',
            'property_account_payable_id': 'l10n_ph_account_200000',
            'property_stock_valuation_account_id': 'l10n_ph_account_110300',
            'code_digits': '6',
        }

    @template('ph', 'res.company')
    def _get_ph_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.ph',
                'bank_account_code_prefix': '1000',
                'cash_account_code_prefix': '1001',
                'transfer_account_code_prefix': '1002',
                'account_default_pos_receivable_account_id': 'l10n_ph_account_110003',
                'income_currency_exchange_account_id': 'l10n_ph_account_710100',
                'expense_currency_exchange_account_id': 'l10n_ph_account_710101',
                'account_journal_suspense_account_id': 'l10n_ph_account_100000',
                'default_cash_difference_income_account_id': 'l10n_ph_account_710102',
                'default_cash_difference_expense_account_id': 'l10n_ph_account_710103',
                'account_sale_tax_id': 'l10n_ph_account_tax_sale_vat_12',
                'account_purchase_tax_id': 'l10n_ph_account_tax_purchase_vat_12',
                'income_account_id': 'l10n_ph_account_430400',
                'expense_account_id': 'l10n_ph_account_620000',
                'transfer_account_id': 'l10n_ph_account_100201',
            },
        }

    @template('ph', 'account.journal')
    def _get_ph_account_journal(self):
        return {
            "bank": {"default_account_id": "l10n_ph_account_100001"},
        }
