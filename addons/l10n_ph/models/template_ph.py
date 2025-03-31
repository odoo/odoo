# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ph')
    def _get_ph_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_ph_110000',
            'property_account_payable_id': 'l10n_ph_200000',
            'property_account_income_categ_id': 'l10n_ph_430400',
            'property_account_expense_categ_id': 'l10n_ph_620000',
            'property_stock_valuation_account_id': 'l10n_ph_110300',
            'property_stock_account_input_categ_id': 'l10n_ph_110302',
            'property_stock_account_output_categ_id': 'l10n_ph_110303',
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
                'account_default_pos_receivable_account_id': 'l10n_ph_110003',
                'income_currency_exchange_account_id': 'l10n_ph_710100',
                'expense_currency_exchange_account_id': 'l10n_ph_710101',
                'account_journal_suspense_account_id': 'l10n_ph_100000',
                'default_cash_difference_income_account_id': 'l10n_ph_710102',
                'default_cash_difference_expense_account_id': 'l10n_ph_710103',
                'account_sale_tax_id': 'l10n_ph_tax_sale_vat_12',
                'account_purchase_tax_id': 'l10n_ph_tax_purchase_vat_12',
            },
        }
