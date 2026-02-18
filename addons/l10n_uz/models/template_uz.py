# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template("uz")
    def _get_uz_template_data(self):
        return {
            "code_digits": 4,
            "property_account_receivable_id": "uz4010",
            "property_account_payable_id": "uz6010",
        }

    @template("uz", "res.company")
    def _get_uz_res_company(self):
        return {
            self.env.company.id: {
                "account_fiscal_country_id": "base.uz",
                "account_journal_suspense_account_id": "uz5120",
                "transfer_account_id": "uz5710",
                "account_sale_tax_id": "l10n_uz_tax_sale_18",
                "account_purchase_tax_id": "l10n_uz_tax_purchase_18",
                "income_account_id": "uz9020",
                "expense_account_id": "uz9120",
                "account_journal_early_pay_discount_loss_account_id": "uz9050",
                "deferred_revenue_account_id": "uz6230",
                "deferred_expense_account_id": "uz3190",
                "income_currency_exchange_account_id": "uz9540",
                "expense_currency_exchange_account_id": "uz9620",
            },
        }
