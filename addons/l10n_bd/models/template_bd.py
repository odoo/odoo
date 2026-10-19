# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('bd')
    def _get_bd_template_data(self):
        return {}

    @template('bd', 'res.company')
    def _get_bd_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.bd',
                'bank_account_code_prefix': '1111',
                'cash_account_code_prefix': '1111',
                'account_default_pos_receivable_account_id': 'l10n_bd_112200',
                'account_journal_suspense_account_id': 'l10n_bd_111400',
                'default_cash_difference_income_account_id': 'l10n_bd_700020',
                'default_cash_difference_expense_account_id': 'l10n_bd_820070',
                'income_currency_exchange_account_id': 'l10n_bd_700010',
                'expense_currency_exchange_account_id': 'l10n_bd_820020',
                'transfer_account_id': 'l10n_bd_111500',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_bd_610330',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_bd_700030',
                'deferred_revenue_account_id': 'l10n_bd_214010',
                'deferred_expense_account_id': 'l10n_bd_114150',
                'fiscalyear_last_month': '6',
                'fiscalyear_last_day': 30,
                'account_sale_tax_id': 'bd_sale_tax_vat_15',
                'account_purchase_tax_id': 'bd_purchase_tax_vat_15',
                'income_account_id': 'l10n_bd_400100',
                'expense_account_id': 'l10n_bd_610010',
                'receivable_account_id': 'l10n_bd_112100',
                'payable_account_id': 'l10n_bd_211010',
                'account_stock_valuation_id': 'l10n_bd_115300',
            },
        }

    @template('bd', 'account.journal')
    def _get_bd_account_journal(self):
        return {
            "tax_adjustment": {
                "name": "Tax Adjustments",
                "code": "TA",
                "type": "general",
                "show_on_dashboard": True,
            },
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'bd':
            return {
                '1111': 'l10n_bd_group_111',
            }.get(code_prefix)
        return super()._get_account_parent_xmlid(code_prefix, template_code)

    @template('bd', 'account.account')
    def _get_bd_account_account(self):
        return {
            'l10n_bd_115300': {
                'account_stock_variation_id': 'l10n_bd_820040',
            },
            'l10n_bd_121200': {'asset_depreciation_account_id': 'l10n_bd_121300', 'asset_expense_account_id': 'l10n_bd_810100'},
            'l10n_bd_121400': {'asset_depreciation_account_id': 'l10n_bd_121500', 'asset_expense_account_id': 'l10n_bd_810200'},
            'l10n_bd_121600': {'asset_depreciation_account_id': 'l10n_bd_121700', 'asset_expense_account_id': 'l10n_bd_810300'},
            'l10n_bd_121800': {'asset_depreciation_account_id': 'l10n_bd_121900', 'asset_expense_account_id': 'l10n_bd_810400'},
            'l10n_bd_122100': {'asset_depreciation_account_id': 'l10n_bd_122200', 'asset_expense_account_id': 'l10n_bd_810500'},
            'l10n_bd_123100': {'asset_depreciation_account_id': 'l10n_bd_123200', 'asset_expense_account_id': 'l10n_bd_810600'},
        }
