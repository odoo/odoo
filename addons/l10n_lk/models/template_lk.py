# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("lk")
    def _get_lk_template_data(self):
        return {
            "code_digits": "6",
        }

    @template("lk", "res.company")
    def _get_lk_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.lk",
                "bank_account_code_prefix": "1101",
                "cash_account_code_prefix": "1102",
                "transfer_account_code_prefix": "1106",
                "transfer_account_id": "l10n_lk_110600",
                "account_default_pos_receivable_account_id": "l10n_lk_120200",
                "income_currency_exchange_account_id": "l10n_lk_420200",
                "expense_currency_exchange_account_id": "l10n_lk_521000",
                "account_journal_suspense_account_id": "l10n_lk_110300",
                "default_cash_difference_expense_account_id": "l10n_lk_521400",
                "default_cash_difference_income_account_id": "l10n_lk_420400",
                "account_journal_early_pay_discount_loss_account_id": "l10n_lk_521600",
                "account_journal_early_pay_discount_gain_account_id": "l10n_lk_420500",
                "account_sale_tax_id": "l10n_lk_tax_sale_18",
                "account_purchase_tax_id": "l10n_lk_tax_purchase_18",
                "deferred_expense_account_id": "l10n_lk_120700",
                "deferred_revenue_account_id": "l10n_lk_210300",
                "income_account_id": "l10n_lk_410100",
                "expense_account_id": "l10n_lk_510200",
                "receivable_account_id": "l10n_lk_120100",
                "payable_account_id": "l10n_lk_210100",
                "account_stock_valuation_id": "l10n_lk_130400",
            },
        }

    @template("lk", "account.journal")
    def _get_lk_account_journal(self):
        return {
            "bank": {"default_account_id": "l10n_lk_110100"},
            "cash": {
                "name": self.env._("Cash"),
                "type": "cash",
                "default_account_id": "l10n_lk_110200",
            },
        }

    @template("lk", "account.account")
    def _get_lk_account_account(self):
        return {
            "l10n_lk_130400": {"account_stock_variation_id": "l10n_lk_510500"},
            "l10n_lk_140200": {"asset_depreciation_account_id": "l10n_lk_140210", "asset_expense_account_id": "l10n_lk_610100"},
            "l10n_lk_140300": {"asset_depreciation_account_id": "l10n_lk_140310", "asset_expense_account_id": "l10n_lk_610200"},
            "l10n_lk_140400": {"asset_depreciation_account_id": "l10n_lk_140410", "asset_expense_account_id": "l10n_lk_610300"},
            "l10n_lk_140500": {"asset_depreciation_account_id": "l10n_lk_140510", "asset_expense_account_id": "l10n_lk_610400"},
            "l10n_lk_140600": {"asset_depreciation_account_id": "l10n_lk_140610", "asset_expense_account_id": "l10n_lk_610500"},
            "l10n_lk_150100": {"asset_depreciation_account_id": "l10n_lk_150110", "asset_expense_account_id": "l10n_lk_610600"},
            "l10n_lk_155200": {"asset_depreciation_account_id": "l10n_lk_155210", "asset_expense_account_id": "l10n_lk_610700"},
            "l10n_lk_160200": {"asset_depreciation_account_id": "l10n_lk_160210", "asset_expense_account_id": "l10n_lk_610800"},
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'lk':
            return {
                '1101': 'l10n_lk_110000',
                '1102': 'l10n_lk_110000',
                '1106': 'l10n_lk_110000',
            }.get(code_prefix)
        return super()._get_account_parent_xmlid(code_prefix, template_code)
