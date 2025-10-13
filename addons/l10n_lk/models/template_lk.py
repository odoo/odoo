# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("lk")
    def _get_lk_template_data(self):
        return {
            "code_digits": "6",
            "property_account_receivable_id": "l10n_lk_account_111000",
            "property_account_payable_id": "l10n_lk_account_220100",
            "property_stock_valuation_account_id": "l10n_lk_account_141000",
        }

    @template("lk", "res.company")
    def _get_lk_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.lk",
                "bank_account_code_prefix": "10100",
                "cash_account_code_prefix": "10110",
                "transfer_account_code_prefix": "10120",
                "transfer_account_id": "l10n_lk_account_101200",
                "account_default_pos_receivable_account_id": "l10n_lk_account_111001",
                "income_currency_exchange_account_id": "l10n_lk_account_422000",
                "expense_currency_exchange_account_id": "l10n_lk_account_704000",
                "account_journal_suspense_account_id": "l10n_lk_account_202000",
                "default_cash_difference_expense_account_id": "l10n_lk_account_706000",
                "default_cash_difference_income_account_id": "l10n_lk_account_414000",
                "account_journal_early_pay_discount_loss_account_id": "l10n_lk_account_705000",
                "account_journal_early_pay_discount_gain_account_id": "l10n_lk_account_423000",
                "account_sale_tax_id": "l10n_lk_tax_sale_18",
                "account_purchase_tax_id": "l10n_lk_tax_purchase_18",
                "deferred_expense_account_id": "l10n_lk_account_131000",
                "deferred_revenue_account_id": "l10n_lk_account_220200",
                "income_account_id": "l10n_lk_account_401000",
                "expense_account_id": "l10n_lk_account_501000",
            },
        }

    @template("lk", "account.journal")
    def _get_lk_account_journal(self):
        return {
            "bank": {"default_account_id": "l10n_lk_account_101000"},
            "cash": {
                "name": self.env._("Cash"),
                "type": "cash",
                "default_account_id": "l10n_lk_account_101100",
            },
        }
