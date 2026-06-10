# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('my')
    def _get_my_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('my', 'res.company')
    def _get_my_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.my',
                'bank_account_code_prefix': '21010',
                'cash_account_code_prefix': '21020',
                'transfer_account_code_prefix': '21070',
                'account_default_pos_receivable_account_id': 'l10n_my_220300',
                'income_currency_exchange_account_id': 'l10n_my_520400',
                'expense_currency_exchange_account_id': 'l10n_my_680200',
                'account_journal_suspense_account_id': 'l10n_my_210400',
                'transfer_account_id': 'l10n_my_210700',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_my_680700',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_my_520600',
                'income_account_id': 'l10n_my_510000',
                'expense_account_id': 'l10n_my_610200',
                'account_stock_valuation_id': 'l10n_my_260400',
                'default_cash_difference_expense_account_id': 'l10n_my_999002',
                'default_cash_difference_income_account_id': 'l10n_my_999001',
                'deferred_expense_account_id': 'l10n_my_230600',
                'deferred_revenue_account_id': 'l10n_my_410400',
                'receivable_account_id': 'l10n_my_220100',
                'payable_account_id': 'l10n_my_440100',
                'account_sale_tax_id': 'l10n_my_tax_sale_10',
                'tax_calculation_rounding_method': 'round_per_line',
            },
        }

    @template('my', 'account.journal')
    def _get_my_account_journal(self):
        return {
            'bank': {
                'default_account_id': 'l10n_my_210100',
            },
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'my':
            return {
                '21010': 'l10n_my_210000',
                '21020': 'l10n_my_210000',
                '21070': 'l10n_my_210000',
            }.get(code_prefix)
        return super()._get_account_parent_xmlid(code_prefix, template_code)

    @template('my', 'account.account')
    def _get_my_account_account(self):
        return {
            'l10n_my_260400': {
                'account_stock_variation_id': 'l10n_my_611100',
            },
            'l10n_my_110100': {'asset_depreciation_account_id': 'l10n_my_110110', 'asset_expense_account_id': 'l10n_my_700100'},
            'l10n_my_110200': {'asset_depreciation_account_id': 'l10n_my_110210', 'asset_expense_account_id': 'l10n_my_700200'},
            'l10n_my_110300': {'asset_depreciation_account_id': 'l10n_my_110310', 'asset_expense_account_id': 'l10n_my_700300'},
            'l10n_my_110400': {'asset_depreciation_account_id': 'l10n_my_110410', 'asset_expense_account_id': 'l10n_my_700400'},
            'l10n_my_110500': {'asset_depreciation_account_id': 'l10n_my_110510', 'asset_expense_account_id': 'l10n_my_700500'},
            'l10n_my_110600': {'asset_depreciation_account_id': 'l10n_my_110610', 'asset_expense_account_id': 'l10n_my_700600'},
            'l10n_my_110700': {'asset_depreciation_account_id': 'l10n_my_110710', 'asset_expense_account_id': 'l10n_my_700700'},
            'l10n_my_110800': {'asset_depreciation_account_id': 'l10n_my_110810', 'asset_expense_account_id': 'l10n_my_700800'},
            'l10n_my_115100': {'asset_depreciation_account_id': 'l10n_my_115110', 'asset_expense_account_id': 'l10n_my_700900'},
            'l10n_my_118100': {'asset_depreciation_account_id': 'l10n_my_118120', 'asset_expense_account_id': 'l10n_my_701000'},
            'l10n_my_120100': {'asset_depreciation_account_id': 'l10n_my_120110', 'asset_expense_account_id': 'l10n_my_701100'},
            'l10n_my_120200': {'asset_depreciation_account_id': 'l10n_my_120210', 'asset_expense_account_id': 'l10n_my_701200'},
            'l10n_my_120300': {'asset_depreciation_account_id': 'l10n_my_120310', 'asset_expense_account_id': 'l10n_my_701300'},
            'l10n_my_120400': {'asset_depreciation_account_id': 'l10n_my_120410', 'asset_expense_account_id': 'l10n_my_701400'},
        }
