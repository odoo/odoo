# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('kr')
    def _get_kr_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('kr', 'res.company')
    def _get_kr_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'receivable_account_id': 'l10n_kr_103100',
                'payable_account_id': 'l10n_kr_210210',
                'account_fiscal_country_id': 'base.kr',
                'bank_account_code_prefix': '10114',
                'cash_account_code_prefix': '10110',
                'transfer_account_code_prefix': '10118',
                'account_default_pos_receivable_account_id': 'l10n_kr_103110',
                'income_currency_exchange_account_id': 'l10n_kr_906000',
                'expense_currency_exchange_account_id': 'l10n_kr_956000',
                'account_journal_suspense_account_id': 'l10n_kr_101170',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_kr_952000',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_kr_913000',
                'account_production_wip_account_id': 'l10n_kr_115410',
                'account_production_wip_overhead_account_id': 'l10n_kr_515000',
                'income_account_id': 'l10n_kr_401000',
                'expense_account_id': 'l10n_kr_451000',
                'transfer_account_id': 'l10n_kr_101180',
                'account_stock_valuation_id': 'l10n_kr_115210',
                'default_cash_difference_expense_account_id': 'l10n_kr_965000',
                'default_cash_difference_income_account_id': 'l10n_kr_914000',
                'deferred_expense_account_id': 'l10n_kr_104110',
                'deferred_revenue_account_id': 'l10n_kr_210960',
            },
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'kr':
            return {
                '10110': 'l10n_kr_101100',
                '10114': 'l10n_kr_101100',
                '10118': 'l10n_kr_101100',
            }.get(code_prefix)
        return super()._get_account_parent_xmlid(code_prefix, template_code)

    @template('kr', 'account.journal')
    def _get_kr_account_journal(self):
        return {
            'bank': {
                'default_account_id': 'l10n_kr_101140',
            },
            'cash': {
                'name': _('Cash'),
                'type': 'cash',
                'default_account_id': 'l10n_kr_101110',
            },
        }

    @template('kr', 'account.account')
    def _get_kr_account_account(self):
        return {
            'l10n_kr_115110': {'account_stock_variation_id': 'l10n_kr_451000'},
            'l10n_kr_115210': {'account_stock_variation_id': 'l10n_kr_452000'},
            'l10n_kr_115310': {'account_stock_variation_id': 'l10n_kr_453000'},
            'l10n_kr_122210': {'asset_depreciation_account_id': 'l10n_kr_122211', 'asset_expense_account_id': 'l10n_kr_820000'},
            'l10n_kr_122220': {'asset_depreciation_account_id': 'l10n_kr_122221', 'asset_expense_account_id': 'l10n_kr_821000'},
            'l10n_kr_122230': {'asset_depreciation_account_id': 'l10n_kr_122231', 'asset_expense_account_id': 'l10n_kr_822000'},
            'l10n_kr_122240': {'asset_depreciation_account_id': 'l10n_kr_122241', 'asset_expense_account_id': 'l10n_kr_823000'},
            'l10n_kr_122250': {'asset_depreciation_account_id': 'l10n_kr_122251', 'asset_expense_account_id': 'l10n_kr_824000'},
            'l10n_kr_122260': {'asset_depreciation_account_id': 'l10n_kr_122261', 'asset_expense_account_id': 'l10n_kr_825000'},
            'l10n_kr_124910': {'asset_depreciation_account_id': 'l10n_kr_124911', 'asset_expense_account_id': 'l10n_kr_826300'},
        }
