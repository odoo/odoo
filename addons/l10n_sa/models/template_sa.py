# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('sa')
    def _get_sa_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('sa', 'res.company')
    def _get_sa_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.sa',
                'tax_calculation_rounding_method': 'round_globally',
                'bank_account_code_prefix': '160',
                'cash_account_code_prefix': '105',
                'transfer_account_id': 'sa_account_170101',
                'account_default_pos_receivable_account_id': 'sa_account_102012',
                'income_currency_exchange_account_id': 'sa_account_500011',
                'expense_currency_exchange_account_id': 'sa_account_400053',
                'account_journal_suspense_account_id': 'sa_account_160103',
                'account_journal_early_pay_discount_loss_account_id': 'sa_account_430800',
                'account_journal_early_pay_discount_gain_account_id': 'sa_account_510500',
                'default_cash_difference_income_account_id': 'sa_account_999001',
                'default_cash_difference_expense_account_id': 'sa_account_999002',
                'account_sale_tax_id': 'sa_sales_tax_15',
                'account_purchase_tax_id': 'sa_purchase_tax_15',
                'expense_account_id': 'sa_account_400001',
                'income_account_id': 'sa_account_500001',
                'receivable_account_id': 'sa_account_102011',
                'payable_account_id': 'sa_account_201002',
                'deferred_expense_account_id': 'sa_account_104020',
                'deferred_revenue_account_id': 'sa_account_201018',
                'account_cash_basis_base_account_id': 'sa_account_201030',
                'account_stock_valuation_id': 'sa_account_131100',
                'paperformat_id': 'l10n_sa.paperformat_l10n_sa_a4',
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
                'sequence': 10,
            },
            "ifrs16": {
                'name': 'IFRS 16 Right of Use Asset',
                'code': 'IFRS',
                'type': 'general',
                'show_on_dashboard': True,
                'sequence': 11,
            },
            "zakat": {
                'name': 'Zakat',
                'code': 'ZAKAT',
                'type': 'general',
                'show_on_dashboard': True,
                'sequence': 11,
            },
            'bank': {
                'default_account_id': 'sa_account_160100',
            },
        }

    @template('sa', 'account.account')
    def _get_sa_account_account(self):
        return {
            'sa_account_100105': {'asset_depreciation_account_id': 'sa_account_100105', 'asset_expense_account_id': 'sa_account_401002'},
            'sa_account_100106': {'asset_depreciation_account_id': 'sa_account_100106', 'asset_expense_account_id': 'sa_account_401003'},
            'sa_account_100107': {'asset_depreciation_account_id': 'sa_account_100107', 'asset_expense_account_id': 'sa_account_401004'},
            'sa_account_100108': {'asset_depreciation_account_id': 'sa_account_100108', 'asset_expense_account_id': 'sa_account_401006'},
            'sa_account_100109': {'asset_depreciation_account_id': 'sa_account_100109', 'asset_expense_account_id': 'sa_account_401001'},
            'sa_account_100110': {'asset_depreciation_account_id': 'sa_account_100110', 'asset_expense_account_id': 'sa_account_401007'},
            'sa_account_100111': {'asset_depreciation_account_id': 'sa_account_100111', 'asset_expense_account_id': 'sa_account_401008'},
            'sa_account_100112': {'asset_depreciation_account_id': 'sa_account_100112', 'asset_expense_account_id': 'sa_account_401005'},
            'sa_account_131100': {
                'account_stock_variation_id': 'sa_account_400001',
            },
        }
