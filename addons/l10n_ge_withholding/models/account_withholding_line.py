from collections import defaultdict

from odoo import api, fields, models


class AccountWithholdingLine(models.AbstractModel):
    _inherit = "account.withholding.line"

    tax_id = fields.Many2one(
        domain="[('type_tax_use', '=', type_tax_use), ('is_withholding_tax', '=', True)] + (l10n_ge_tax_id_domain or [])",
    )
    l10n_ge_treaty_exempt_amount = fields.Monetary(
        currency_field="comodel_currency_id",
        string="Withheld Treaty Exempt",
        help="Amount an international tax treaty exempts from withholding. Informational only: it"
        " changes neither the withheld amount nor the journal entry amounts.",
    )
    l10n_ge_tax_id_domain = fields.Json(
        string="Withholding tax category domain",
        help="Restricts the withholding taxes to the categories of the recipient, when it has some.",
        compute="_compute_l10n_ge_tax_id_domain",
    )

    @api.depends("country_code")
    def _compute_l10n_ge_tax_id_domain(self):
        for line in self:
            categories = line._get_comodel_partner().l10n_ge_wht_category_ids
            if line.country_code == "GE" and categories:
                line.l10n_ge_tax_id_domain = [("l10n_ge_wht_category_ids", "in", categories.ids)]
            else:
                line.l10n_ge_tax_id_domain = []

    def _prepare_withholding_amls_create_values(self):
        # EXTENDS l10n_account_withholding_tax
        aml_create_values_list = super()._prepare_withholding_amls_create_values()
        lines_by_tax = self.filtered(lambda line: line.tax_id.country_code == "GE").grouped("tax_id")
        tax_lines_vals_by_tax = defaultdict(list)
        for vals in aml_create_values_list:
            if tax_rep_id := vals.get("tax_repartition_line_id"):
                tax = self.env["account.tax.repartition.line"].browse(tax_rep_id).tax_id
                if tax in lines_by_tax:
                    vals["l10n_ge_treaty_exempt_amount"] = 0.0
                    tax_lines_vals_by_tax[tax].append(vals)

        company = self.company_id
        for tax, tax_lines_vals in tax_lines_vals_by_tax.items():
            for line in lines_by_tax[tax]:
                tax_line_vals = next((
                    vals for vals in tax_lines_vals
                    if len(tax_lines_vals) == 1 or vals["analytic_distribution"] == line.analytic_distribution
                ), None)
                if not tax_line_vals:
                    continue
                rate = self.env["res.currency"]._get_conversion_rate(
                    company.currency_id, line.comodel_currency_id, company, line.comodel_date
                )
                if rate:
                    sign = 1 if line.comodel_payment_type == "inbound" else -1
                    amount = company.currency_id.round(line.l10n_ge_treaty_exempt_amount / rate)
                    tax_line_vals["l10n_ge_treaty_exempt_amount"] += sign * amount
        return aml_create_values_list
