# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cn')
    def _get_cn_template_data(self):
        return {
            'name': _('Accounting Standards for Small Business Enterprises'),
            'code_digits': 4,
            'parent': 'cn_common',
        }

    @template('cn', 'res.company')
    def _get_cn_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cn',
                'transfer_account_code_prefix': '1005',
                'income_currency_exchange_account_id': 'l10n_cn_account_530102',
                'expense_currency_exchange_account_id': 'l10n_cn_account_560302',
                'account_journal_suspense_account_id': 'l10n_cn_account_1004',
                'transfer_account_id': 'l10n_cn_account_1005',
                'account_production_wip_account_id': 'l10n_cn_account_4001',
                'default_cash_difference_income_account_id': 'l10n_cn_account_530103',
                'default_cash_difference_expense_account_id': 'l10n_cn_account_560303',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_cn_account_530104',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_cn_account_560304',
                'account_production_wip_overhead_account_id': 'l10n_cn_account_4101',
                'account_sale_tax_id': 'l10n_cn_sales_excluded_13',
                'account_purchase_tax_id': 'l10n_cn_purchase_excluded_13',
                'expense_account_id': 'l10n_cn_account_5401',
                'income_account_id': 'l10n_cn_account_5001',
                'tax_calculation_rounding_method': 'round_per_line',
                'account_stock_valuation_id': 'l10n_cn_common_account_1403',
            },
        }

    @template('cn', 'account.account')
    def _get_cn_account_account(self):
        return {
            'l10n_cn_common_account_160101': {'asset_depreciation_account_id': 'l10n_cn_common_account_160201', 'asset_expense_account_id': 'l10n_cn_account_5602'},
            'l10n_cn_common_account_160102': {'asset_depreciation_account_id': 'l10n_cn_common_account_160202', 'asset_expense_account_id': 'l10n_cn_account_5602'},
            'l10n_cn_common_account_160103': {'asset_depreciation_account_id': 'l10n_cn_common_account_160203', 'asset_expense_account_id': 'l10n_cn_account_5602'},
            'l10n_cn_common_account_160104': {'asset_depreciation_account_id': 'l10n_cn_common_account_160204', 'asset_expense_account_id': 'l10n_cn_account_5602'},
            'l10n_cn_common_account_160105': {'asset_depreciation_account_id': 'l10n_cn_common_account_160205', 'asset_expense_account_id': 'l10n_cn_account_5602'},
            'l10n_cn_common_account_160106': {'asset_depreciation_account_id': 'l10n_cn_common_account_160206', 'asset_expense_account_id': 'l10n_cn_account_5602'},
            'l10n_cn_common_account_1403': {
                'account_stock_variation_id': 'l10n_cn_account_5601',
            },
        }
