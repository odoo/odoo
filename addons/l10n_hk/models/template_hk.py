# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hk')
    def _get_hk_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('hk', 'res.company')
    def _get_hk_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'receivable_account_id': 'l10n_hk_120100',
                'payable_account_id': 'l10n_hk_220100',
                'account_fiscal_country_id': 'base.hk',
                'bank_account_code_prefix': '11010',
                'cash_account_code_prefix': '11020',
                'transfer_account_code_prefix': '11070',
                'account_default_pos_receivable_account_id': 'l10n_hk_120200',
                'income_currency_exchange_account_id': 'l10n_hk_420300',
                'expense_currency_exchange_account_id': 'l10n_hk_529400',
                'account_journal_suspense_account_id': 'l10n_hk_110400',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_hk_529500',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_hk_420400',
                'income_account_id': 'l10n_hk_410100',
                'expense_account_id': 'l10n_hk_510100',
                'transfer_account_id': 'l10n_hk_110700',
                'account_stock_valuation_id': 'l10n_hk_130100',
                'default_cash_difference_expense_account_id': 'l10n_hk_999002',
                'default_cash_difference_income_account_id': 'l10n_hk_999001',
                'deferred_expense_account_id': 'l10n_hk_125300',
                'deferred_revenue_account_id': 'l10n_hk_210200',
            },
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'hk':
            return {
                '11010': 'l10n_hk_110000',
                '11020': 'l10n_hk_110000',
                '11070': 'l10n_hk_110000',
            }.get(code_prefix)
        return super()._get_account_parent_xmlid(code_prefix, template_code)

    @template('hk', 'account.journal')
    def _get_hk_account_journal(self):
        return {
            'bank': {
                'default_account_id': 'l10n_hk_110100',
            },
        }

    @template('hk', 'account.account')
    def _get_hk_account_account(self):
        return {
            'l10n_hk_130100': {
                'account_stock_variation_id': 'l10n_hk_511000',
            },
            'l10n_hk_150100': {'asset_depreciation_account_id': 'l10n_hk_150110', 'asset_expense_account_id': 'l10n_hk_650100'},
            'l10n_hk_150200': {'asset_depreciation_account_id': 'l10n_hk_150210', 'asset_expense_account_id': 'l10n_hk_650200'},
            'l10n_hk_150300': {'asset_depreciation_account_id': 'l10n_hk_150310', 'asset_expense_account_id': 'l10n_hk_650300'},
            'l10n_hk_150400': {'asset_depreciation_account_id': 'l10n_hk_150410', 'asset_expense_account_id': 'l10n_hk_650400'},
            'l10n_hk_150500': {'asset_depreciation_account_id': 'l10n_hk_150510', 'asset_expense_account_id': 'l10n_hk_650500'},
            'l10n_hk_150600': {'asset_depreciation_account_id': 'l10n_hk_150610', 'asset_expense_account_id': 'l10n_hk_650600'},
            'l10n_hk_155100': {'asset_depreciation_account_id': 'l10n_hk_155110', 'asset_expense_account_id': 'l10n_hk_650700'},
            'l10n_hk_155200': {'asset_depreciation_account_id': 'l10n_hk_155210', 'asset_expense_account_id': 'l10n_hk_650800'},
            'l10n_hk_155300': {'asset_depreciation_account_id': 'l10n_hk_155310', 'asset_expense_account_id': 'l10n_hk_650900'},
            'l10n_hk_160100': {'asset_depreciation_account_id': 'l10n_hk_160110', 'asset_expense_account_id': 'l10n_hk_651000'},
            'l10n_hk_160200': {'asset_depreciation_account_id': 'l10n_hk_160210', 'asset_expense_account_id': 'l10n_hk_651100'},
            'l10n_hk_160300': {'asset_depreciation_account_id': 'l10n_hk_160310', 'asset_expense_account_id': 'l10n_hk_651200'},
            'l10n_hk_160400': {'asset_depreciation_account_id': 'l10n_hk_160410', 'asset_expense_account_id': 'l10n_hk_651300'},
        }
