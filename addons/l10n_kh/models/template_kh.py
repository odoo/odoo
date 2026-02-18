# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('kh')
    def _get_kh_template_data(self):
        return {
            'code_digits': '5',
            'property_account_receivable_id': 'l10n_kh_50000',
            'property_account_payable_id': 'l10n_kh_60000',
            'property_account_expense_categ_id': 'l10n_kh_30000',
            'property_account_income_categ_id': 'l10n_kh_20001',
            'property_stock_valuation_account_id': 'l10n_kh_15000',
            'property_stock_account_input_categ_id': 'l10n_kh_15001',
            'property_stock_account_output_categ_id': 'l10n_kh_15002',
            'deferred_expense_account_id': 'l10n_kh_11000',
            'deferred_revenue_account_id': 'l10n_kh_85000'
        }

    @template('kh', 'res.company')
    def _get_kh_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.kh',
                'bank_account_code_prefix': '100',
                'cash_account_code_prefix': '101',
                'transfer_account_code_prefix': '110',
                'transfer_account_id': 'l10n_kh_11003',
                'account_default_pos_receivable_account_id': 'l10n_kh_50001',
                'income_currency_exchange_account_id': 'l10n_kh_21200',
                'expense_currency_exchange_account_id': 'l10n_kh_40011',
                'account_journal_suspense_account_id': 'l10n_kh_11000',
                'account_journal_payment_credit_account_id': 'l10n_kh_11002',
                'account_journal_payment_debit_account_id': 'l10n_kh_11001',
                'default_cash_difference_expense_account_id': 'l10n_kh_40001',
                'default_cash_difference_income_account_id': 'l10n_kh_21000',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_kh_91105',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_kh_91105',
                'account_sale_tax_id': 'l10n_kh_10_sales_vat',
                'account_purchase_tax_id': 'l10n_kh_10_purchase_vat',
            },
        }

    @template('kh', 'account.journal')
    def _get_kh_account_journal(self):
        return {
            'cash': {'default_account_id': 'l10n_kh_10000'},
            'bank': {'default_account_id': 'l10n_kh_10100'},
        }
