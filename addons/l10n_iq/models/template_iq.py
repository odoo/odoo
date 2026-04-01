# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("iq")
    def _get_iq_template_data(self):
        return {
            "property_account_receivable_id": "iq_account_100201",
            "property_account_payable_id": "iq_account_200101",
            "property_account_expense_id": "iq_account_500101",
            "property_account_income_id": "iq_account_400101",
            "property_stock_valuation_account_id": "iq_account_100502",
            "property_stock_account_production_cost_id": "iq_account_100505",
            "code_digits": "6",
        }

    @template("iq", "res.company")
    def _get_iq_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.iq",
                "bank_account_code_prefix": "1000",
                "cash_account_code_prefix": "1009",
                "transfer_account_code_prefix": "1001",
                "account_default_pos_receivable_account_id": "iq_account_100202",
                "income_currency_exchange_account_id": "iq_account_400301",
                "expense_currency_exchange_account_id": "iq_account_500903",
                "account_journal_suspense_account_id": "iq_account_100102",
                "account_journal_early_pay_discount_loss_account_id": "iq_account_501107",
                "account_journal_early_pay_discount_gain_account_id": "iq_account_400304",
                "default_cash_difference_income_account_id": "iq_account_400302",
                "default_cash_difference_expense_account_id": "iq_account_500909",
                "deferred_expense_account_id": "iq_account_100416",
                "deferred_revenue_account_id": "iq_account_200401",
                "expense_account_id": "iq_account_500101",
                "income_account_id": "iq_account_400101",
            },
        }
