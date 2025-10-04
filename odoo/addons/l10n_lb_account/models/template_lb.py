# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("lb")
    def _get_lb_template_data(self):
        return {
            "property_account_receivable_id": "lb_account_413004",
            "property_account_payable_id": "lb_account_403501",
            "property_account_expense_categ_id": "lb_account_601101",
            "property_account_income_categ_id": "lb_account_701000",
            "property_account_expense_id": "lb_account_601101",
            "property_account_income_id": "lb_account_701000",
            "property_stock_valuation_account_id": "lb_account_370001",
            "property_stock_account_input_categ_id": "lb_account_370002",
            "property_stock_account_output_categ_id": "lb_account_370003",
            "property_stock_account_production_cost_id": "lb_account_370004",
            "tax_payable_account_id": "lb_account_442001",
            "tax_receivable_account_id": "lb_account_442201",
            "code_digits": "6",
        }

    @template("lb", "res.company")
    def _get_leb_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.lb",
                "bank_account_code_prefix": "5121",
                "cash_account_code_prefix": "5300",
                "transfer_account_code_prefix": "5400",
                "account_default_pos_receivable_account_id": "lb_account_413003",
                "income_currency_exchange_account_id": "lb_account_775100",
                "expense_currency_exchange_account_id": "lb_account_675100",
                "account_journal_suspense_account_id": "lb_account_540002",
                "account_journal_early_pay_discount_loss_account_id": "lb_account_709001",
                "account_journal_early_pay_discount_gain_account_id": "lb_account_778001",
                "account_journal_payment_debit_account_id": "lb_account_540003",
                "account_journal_payment_credit_account_id": "lb_account_540004",
                "default_cash_difference_income_account_id": "lb_account_701000",
                "default_cash_difference_expense_account_id": "lb_account_601101",
                "deferred_expense_account_id": "lb_account_472001",
                "deferred_revenue_account_id": "lb_account_473001",
            },
        }
