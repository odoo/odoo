from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_de_datev_code = fields.Char(
        size=4,
        tracking=True,
        help="4 digits code use by Datev",
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_product_accounts(self, fiscal_pos=None):
        """As taxes with a different rate need a different income/expense account, we add this logic in case people only use
        invoicing to not be blocked by the above constraint"""
        result = super()._get_product_accounts(fiscal_pos=fiscal_pos)
        company = self.env.company
        if company.account_fiscal_country_id.code == "DE":
            # Only what is actually replaced goes through the fiscal position:
            # super() has already mapped what it returned, and map_account is not
            # idempotent when a position chains one account onto another.
            replaced = {}
            if not self.property_account_income_id:
                taxes = self.taxes_id.filtered_domain(
                    self.env["account.tax"]._check_company_domain(company)
                )
                if not result["income"] or (
                    result["income"].tax_ids
                    and taxes
                    and taxes[0] not in result["income"].tax_ids
                ):
                    result_income = (
                        self.env["account.account"]
                        .with_company(company)
                        .search(
                            [
                                *self.env["account.account"]._check_company_domain(
                                    company
                                ),
                                ("internal_group", "=", "income"),
                                ("tax_ids", "in", taxes.ids),
                            ],
                            limit=1,
                        )
                    )
                    if result_income:
                        replaced["income"] = result_income
            if not self.property_account_expense_id:
                supplier_taxes = self.supplier_taxes_id.filtered_domain(
                    self.env["account.tax"]._check_company_domain(company)
                )
                if not result["expense"] or (
                    result["expense"].tax_ids
                    and supplier_taxes
                    and supplier_taxes[0] not in result["expense"].tax_ids
                ):
                    result_expense = (
                        self.env["account.account"]
                        .with_company(company)
                        .search(
                            [
                                *self.env["account.account"]._check_company_domain(
                                    company
                                ),
                                ("internal_group", "=", "expense"),
                                ("tax_ids", "in", supplier_taxes.ids),
                            ],
                            limit=1,
                        )
                    )
                    if result_expense:
                        replaced["expense"] = result_expense
            result.update(self._map_product_accounts(replaced, fiscal_pos))
        return result
