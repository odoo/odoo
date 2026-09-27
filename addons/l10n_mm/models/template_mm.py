# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mm')
    def _get_mm_template_data(self):
        return {
            'code_digits': '4',
        }

    @template('mm', 'res.company')
    def _get_mm_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.mm',
                'bank_account_code_prefix': '1030',
                'cash_account_code_prefix': '1010',
                'transfer_account_code_prefix': '1050',
                'receivable_account_id': 'l10n_mm_account_1105',
                'payable_account_id': 'l10n_mm_account_2005',
                'account_default_pos_receivable_account_id': 'l10n_mm_account_1110',
                'income_currency_exchange_account_id': 'l10n_mm_account_7025',
                'expense_currency_exchange_account_id': 'l10n_mm_account_8000',
                'account_journal_suspense_account_id': 'l10n_mm_account_1040',
                'default_cash_difference_income_account_id': 'l10n_mm_account_7030',
                'default_cash_difference_expense_account_id': 'l10n_mm_account_8010',
                'account_sale_tax_id': 'l10n_mm_account_tax_sale_5_commercial_tax',
                'account_purchase_tax_id': 'l10n_mm_account_tax_purchase_5_commercial_tax',
                'income_account_id': 'l10n_mm_account_4005',
                'expense_account_id': 'l10n_mm_account_6095',
                'transfer_account_id': 'l10n_mm_account_1050',
                'account_stock_valuation_id': 'l10n_mm_account_1305',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_mm_account_7035',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_mm_account_8015',
                'deferred_revenue_account_id': 'l10n_mm_account_2110',
                'deferred_expense_account_id': 'l10n_mm_account_1520',
            },
        }

    @template('mm', 'account.journal')
    def _get_mm_account_journal(self):
        return {
            'bank': {'default_account_id': 'l10n_mm_account_1030'},
        }

    @template('mm', 'account.account')
    def _get_mm_account_account(self):
        return {
            'l10n_mm_account_1305': {
                'account_stock_expense_id': 'l10n_mm_account_5000',
                'account_stock_variation_id': 'l10n_mm_account_5100',
            },
        }
