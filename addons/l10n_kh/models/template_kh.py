# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('kh')
    def _get_kh_template_data(self):
        return {
            'code_digits': '5',
        }

    @template('kh', 'res.company')
    def _get_kh_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.kh',
                'bank_account_code_prefix': '109',
                'cash_account_code_prefix': '108',
                'transfer_account_code_prefix': '109',
                'transfer_account_id': 'l10n_kh_account_10902',
                'account_default_pos_receivable_account_id': 'l10n_kh_account_10501',
                'income_currency_exchange_account_id': 'l10n_kh_account_42500',
                'expense_currency_exchange_account_id': 'l10n_kh_account_61700',
                'account_journal_suspense_account_id': 'l10n_kh_account_10901',
                'default_cash_difference_expense_account_id': 'l10n_kh_account_61910',
                'default_cash_difference_income_account_id': 'l10n_kh_account_42610',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_kh_account_61900',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_kh_account_42600',
                'account_sale_tax_id': 'l10n_kh_tax_sale_10_m_t',
                'account_purchase_tax_id': 'l10n_kh_tax_purchase_10_m',
                'deferred_expense_account_id': 'l10n_kh_account_10700',
                'deferred_revenue_account_id': 'l10n_kh_account_20500',
                'expense_account_id': 'l10n_kh_account_42800',
                'income_account_id': 'l10n_kh_account_40100',
                'receivable_account_id': 'l10n_kh_account_10500',
                'payable_account_id': 'l10n_kh_account_20400',
                'account_stock_valuation_id': 'l10n_kh_account_10200',
            },
        }

    @template('kh', 'account.journal')
    def _get_kh_account_journal(self):
        return {
            "bank": {"default_account_id": "l10n_kh_account_10900"},
            "cash": {
                "name": self.env._("Cash"),
                "type": "cash",
                "default_account_id": "l10n_kh_account_10800",
            },
        }

    @template('kh', 'account.account')
    def _get_kh_account_account(self):
        return {
            'l10n_kh_account_12300': {'asset_depreciation_account_id': 'l10n_kh_account_12310', 'asset_expense_account_id': 'l10n_kh_account_61401'},
            'l10n_kh_account_12620': {'asset_depreciation_account_id': 'l10n_kh_account_12621', 'asset_expense_account_id': 'l10n_kh_account_61402'},
            'l10n_kh_account_12630': {'asset_depreciation_account_id': 'l10n_kh_account_12631', 'asset_expense_account_id': 'l10n_kh_account_61403'},
            'l10n_kh_account_12640': {'asset_depreciation_account_id': 'l10n_kh_account_12641', 'asset_expense_account_id': 'l10n_kh_account_61403'},
            'l10n_kh_account_12600': {'asset_depreciation_account_id': 'l10n_kh_account_12601', 'asset_expense_account_id': 'l10n_kh_account_61404'},
            'l10n_kh_account_12710': {'asset_depreciation_account_id': 'l10n_kh_account_12711', 'asset_expense_account_id': 'l10n_kh_account_61405'},
        }
