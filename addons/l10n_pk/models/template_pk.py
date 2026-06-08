# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pk')
    def _get_pk_template_data(self):
        return {
            'code_digits': '7',
        }

    @template('pk', 'res.company')
    def _get_pk_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.pk',
                'bank_account_code_prefix': '12501',
                'cash_account_code_prefix': '12501',
                'transfer_account_id': 'l10n_pk_1250500',
                'account_default_pos_receivable_account_id': 'l10n_pk_1221100',
                'account_journal_suspense_account_id': 'l10n_pk_1250400',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_pk_8130100',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_pk_7110300',
                'default_cash_difference_income_account_id': 'l10n_pk_7110400',
                'default_cash_difference_expense_account_id': 'l10n_pk_8130200',
                'income_currency_exchange_account_id': 'l10n_pk_7110600',
                'expense_currency_exchange_account_id': 'l10n_pk_6310200',
                'deferred_expense_account_id': 'l10n_pk_1234000',
                'deferred_revenue_account_id': 'l10n_pk_2110500',
                'account_discount_expense_allocation_id': 'l10n_pk_4110300',
                'account_production_wip_account_id': 'l10n_pk_1210200',
                'fiscalyear_last_month': '6',
                'fiscalyear_last_day': 30,
                'account_sale_tax_id': 'pk_sales_tax_gst_18',
                'account_purchase_tax_id': 'pk_purchase_tax_gst_18',
                'income_account_id': 'l10n_pk_4110100',
                'expense_account_id': 'l10n_pk_6110100',
                'receivable_account_id': 'l10n_pk_1220100',
                'payable_account_id': 'l10n_pk_2110100',
                'account_stock_valuation_id': 'l10n_pk_1210100',
            },
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'pk':
            return {
                '12501': 'l10n_pk_group_125',
            }.get(code_prefix)
        return super()._get_account_parent_xmlid(code_prefix, template_code)

    @template('pk', 'account.account')
    def _get_pk_account_account(self):
        return {
            'l10n_pk_1110300': {'asset_depreciation_account_id': 'l10n_pk_1110400', 'asset_expense_account_id': 'l10n_pk_8110300'},
            'l10n_pk_1110500': {'asset_depreciation_account_id': 'l10n_pk_1110600', 'asset_expense_account_id': 'l10n_pk_8110500'},
            'l10n_pk_1110700': {'asset_depreciation_account_id': 'l10n_pk_1110800', 'asset_expense_account_id': 'l10n_pk_8110700'},
            'l10n_pk_1110900': {'asset_depreciation_account_id': 'l10n_pk_1111000', 'asset_expense_account_id': 'l10n_pk_8110900'},
            'l10n_pk_1111100': {'asset_depreciation_account_id': 'l10n_pk_1111200', 'asset_expense_account_id': 'l10n_pk_8111400'},
            'l10n_pk_1111300': {'asset_depreciation_account_id': 'l10n_pk_1111400', 'asset_expense_account_id': 'l10n_pk_8111300'},
            'l10n_pk_1111500': {'asset_depreciation_account_id': 'l10n_pk_1111600', 'asset_expense_account_id': 'l10n_pk_8111500'},
            'l10n_pk_1111700': {'asset_depreciation_account_id': 'l10n_pk_1111800', 'asset_expense_account_id': 'l10n_pk_8111700'},
            'l10n_pk_1120100': {'asset_depreciation_account_id': 'l10n_pk_1120200', 'asset_expense_account_id': 'l10n_pk_8120100'},
            'l10n_pk_1210100': {
                'account_stock_variation_id': 'l10n_pk_6110100',
            },
        }
