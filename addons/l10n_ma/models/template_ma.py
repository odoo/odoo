# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ma')
    def _get_ma_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'pcg_34211',
            'property_account_payable_id': 'pcg_44111',
            'display_invoice_amount_total_words': True,
        }

    @template('ma', 'res.company')
    def _get_ma_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ma',
                'bank_account_code_prefix': '5141',
                'cash_account_code_prefix': '51611',
                'transfer_account_code_prefix': '5115',
                'account_default_pos_receivable_account_id': 'pcg_34218',
                'income_currency_exchange_account_id': 'pcg_7331',
                'expense_currency_exchange_account_id': 'pcg_6331',
                'account_journal_suspense_account_id': 'pcg_3497',
                'default_cash_difference_income_account_id': 'pcg_73861',
                'default_cash_difference_expense_account_id': 'pcg_63861',
                'account_journal_early_pay_discount_gain_account_id': 'pcg_73862',
                'account_journal_early_pay_discount_loss_account_id': 'pcg_63862',
                'account_sale_tax_id': 'vat_out_20_80',
                'account_purchase_tax_id': 'vat_in_20_146',
                'income_account_id': 'pcg_7111',
                'expense_account_id': 'pcg_6111',
                'tax_exigibility': 'True',
                'account_stock_valuation_id': 'pcg_31211',
            },
        }

    @template('ma', 'account.account')
    def _get_ma_account_account(self):
        return {
            'pcg_2313': {'asset_depreciation_account_id': 'pcg_28313', 'asset_expense_account_id': 'pcg_61931'},
            'pcg_2314': {'asset_depreciation_account_id': 'pcg_28314', 'asset_expense_account_id': 'pcg_61931'},
            'pcg_2316': {'asset_depreciation_account_id': 'pcg_28316', 'asset_expense_account_id': 'pcg_61931'},
            'pcg_2318': {'asset_depreciation_account_id': 'pcg_28318', 'asset_expense_account_id': 'pcg_61931'},
            'pcg_23211': {'asset_depreciation_account_id': 'pcg_28321', 'asset_expense_account_id': 'pcg_61932'},
            'pcg_23214': {'asset_depreciation_account_id': 'pcg_28321', 'asset_expense_account_id': 'pcg_61932'},
            'pcg_23218': {'asset_depreciation_account_id': 'pcg_28321', 'asset_expense_account_id': 'pcg_61932'},
            'pcg_2323': {'asset_depreciation_account_id': 'pcg_28323', 'asset_expense_account_id': 'pcg_61932'},
            'pcg_2325': {'asset_depreciation_account_id': 'pcg_28325', 'asset_expense_account_id': 'pcg_61932'},
            'pcg_2327': {'asset_depreciation_account_id': 'pcg_28327', 'asset_expense_account_id': 'pcg_61932'},
            'pcg_2328': {'asset_depreciation_account_id': 'pcg_28328', 'asset_expense_account_id': 'pcg_61932'},
            'pcg_2331': {'asset_depreciation_account_id': 'pcg_28331', 'asset_expense_account_id': 'pcg_61933'},
            'pcg_23321': {'asset_depreciation_account_id': 'pcg_28332', 'asset_expense_account_id': 'pcg_61933'},
            'pcg_23324': {'asset_depreciation_account_id': 'pcg_28332', 'asset_expense_account_id': 'pcg_61933'},
            'pcg_2333': {'asset_depreciation_account_id': 'pcg_28333', 'asset_expense_account_id': 'pcg_61933'},
            'pcg_2338': {'asset_depreciation_account_id': 'pcg_28338', 'asset_expense_account_id': 'pcg_61933'},
            'pcg_2340': {'asset_depreciation_account_id': 'pcg_2834', 'asset_expense_account_id': 'pcg_61934'},
            'pcg_2351': {'asset_depreciation_account_id': 'pcg_28351', 'asset_expense_account_id': 'pcg_61935'},
            'pcg_2352': {'asset_depreciation_account_id': 'pcg_28352', 'asset_expense_account_id': 'pcg_61935'},
            'pcg_2355': {'asset_depreciation_account_id': 'pcg_28355', 'asset_expense_account_id': 'pcg_61935'},
            'pcg_2356': {'asset_depreciation_account_id': 'pcg_28356', 'asset_expense_account_id': 'pcg_61935'},
            'pcg_2358': {'asset_depreciation_account_id': 'pcg_28358', 'asset_expense_account_id': 'pcg_61935'},
            'pcg_2380': {'asset_depreciation_account_id': 'pcg_2838', 'asset_expense_account_id': 'pcg_61938'},
            'pcg_31211': {
                'account_stock_expense_id': 'pcg_61211',
                'account_stock_variation_id': 'pcg_61241',
            },
        }
