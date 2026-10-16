# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('la')
    def _get_la_template_data(self):
        return {
            # Official codes are kept as they are: 3 is the shortest postable code, so nothing is padded.
            'code_digits': '3',
        }

    @template('la', 'res.company')
    def _get_la_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.la',
                'bank_account_code_prefix': '102',
                'cash_account_code_prefix': '101',
                'transfer_account_code_prefix': '58',
                'receivable_account_id': 'l10n_la_account_1211',
                'payable_account_id': 'l10n_la_account_401',
                'account_default_pos_receivable_account_id': 'l10n_la_account_1211',
                'income_account_id': 'l10n_la_account_707',
                'expense_account_id': 'l10n_la_account_607',
                'income_currency_exchange_account_id': 'l10n_la_account_763',
                'expense_currency_exchange_account_id': 'l10n_la_account_663',
                'account_journal_suspense_account_id': 'l10n_la_account_518',
                'transfer_account_id': 'l10n_la_account_583',
                'default_cash_difference_income_account_id': 'l10n_la_account_758',
                'default_cash_difference_expense_account_id': 'l10n_la_account_658',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_la_account_762',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_la_account_662',
                'deferred_expense_account_id': 'l10n_la_account_146',
                'deferred_revenue_account_id': 'l10n_la_account_447',
                'account_stock_valuation_id': 'l10n_la_account_137',
                'account_production_wip_account_id': 'l10n_la_account_1331',
                'account_sale_tax_id': 'l10n_la_tax_sale_vat_10',
                'account_purchase_tax_id': 'l10n_la_tax_purchase_vat_10',
            },
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'la':
            return {
                '101': 'l10n_la_account_101',
                '102': 'l10n_la_account_102',
                '58': 'l10n_la_account_58',
            }.get(code_prefix)
        return super()._get_account_parent_xmlid(code_prefix, template_code)

    @template('la', 'account.journal')
    def _get_la_account_journal(self):
        return {
            'bank': {'default_account_id': 'l10n_la_account_1021'},
            'cash': {
                'name': self.env._("Cash"),
                'type': 'cash',
                'default_account_id': 'l10n_la_account_1011',
            },
        }

    @template('la', 'account.account')
    def _get_la_account_account(self):
        return {
            'l10n_la_account_137': {'account_stock_variation_id': 'l10n_la_account_607'},
            'l10n_la_account_222': {'asset_depreciation_account_id': 'l10n_la_account_2822', 'asset_expense_account_id': 'l10n_la_account_68222'},
            'l10n_la_account_223': {'asset_depreciation_account_id': 'l10n_la_account_2823', 'asset_expense_account_id': 'l10n_la_account_68223'},
            'l10n_la_account_224': {'asset_depreciation_account_id': 'l10n_la_account_2824', 'asset_expense_account_id': 'l10n_la_account_68224'},
            'l10n_la_account_225': {'asset_depreciation_account_id': 'l10n_la_account_2825', 'asset_expense_account_id': 'l10n_la_account_68225'},
            'l10n_la_account_2411': {'asset_depreciation_account_id': 'l10n_la_account_28411', 'asset_expense_account_id': 'l10n_la_account_68211'},
            'l10n_la_account_2412': {'asset_depreciation_account_id': 'l10n_la_account_28412', 'asset_expense_account_id': 'l10n_la_account_68212'},
            'l10n_la_account_2413': {'asset_depreciation_account_id': 'l10n_la_account_28413', 'asset_expense_account_id': 'l10n_la_account_68213'},
            'l10n_la_account_2414': {'asset_depreciation_account_id': 'l10n_la_account_28414', 'asset_expense_account_id': 'l10n_la_account_68214'},
            'l10n_la_account_2417': {'asset_depreciation_account_id': 'l10n_la_account_28417', 'asset_expense_account_id': 'l10n_la_account_68217'},
            'l10n_la_account_2418': {'asset_depreciation_account_id': 'l10n_la_account_28418', 'asset_expense_account_id': 'l10n_la_account_68218'},
            'l10n_la_account_2421': {'asset_depreciation_account_id': 'l10n_la_account_28421', 'asset_expense_account_id': 'l10n_la_account_68321'},
            'l10n_la_account_2422': {'asset_depreciation_account_id': 'l10n_la_account_28422', 'asset_expense_account_id': 'l10n_la_account_68322'},
            'l10n_la_account_2423': {'asset_depreciation_account_id': 'l10n_la_account_28423', 'asset_expense_account_id': 'l10n_la_account_68323'},
            'l10n_la_account_2428': {'asset_depreciation_account_id': 'l10n_la_account_28428', 'asset_expense_account_id': 'l10n_la_account_68328'},
            'l10n_la_account_2431': {'asset_depreciation_account_id': 'l10n_la_account_28431', 'asset_expense_account_id': 'l10n_la_account_68231'},
            'l10n_la_account_2432': {'asset_depreciation_account_id': 'l10n_la_account_28432', 'asset_expense_account_id': 'l10n_la_account_68232'},
            'l10n_la_account_2433': {'asset_depreciation_account_id': 'l10n_la_account_28433', 'asset_expense_account_id': 'l10n_la_account_68233'},
            'l10n_la_account_2434': {'asset_depreciation_account_id': 'l10n_la_account_28434', 'asset_expense_account_id': 'l10n_la_account_68234'},
            'l10n_la_account_2438': {'asset_depreciation_account_id': 'l10n_la_account_28438', 'asset_expense_account_id': 'l10n_la_account_68238'},
            'l10n_la_account_251': {'asset_depreciation_account_id': 'l10n_la_account_2851', 'asset_expense_account_id': 'l10n_la_account_68251'},
            'l10n_la_account_252': {'asset_depreciation_account_id': 'l10n_la_account_2852', 'asset_expense_account_id': 'l10n_la_account_68252'},
            'l10n_la_account_258': {'asset_depreciation_account_id': 'l10n_la_account_2858', 'asset_expense_account_id': 'l10n_la_account_68258'},
        }
