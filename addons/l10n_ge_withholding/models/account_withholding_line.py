from odoo import fields, models
from odoo.fields import Domain


class AccountWithholdingLine(models.AbstractModel):
    _inherit = "account.withholding.line"

    l10n_ge_treaty_exempt_amount = fields.Monetary(
        currency_field="comodel_currency_id",
        string="Withheld Treaty Exempt",
        help="Part of the withheld amount that an international tax treaty exempts. Informational"
        " only: it changes neither the withheld amount nor the journal entry.",
    )
    l10n_ge_tax_id_custom_domain = fields.Json(
        string="Withholding tax domain",
        help="Domain restricting the withholding taxes to the ones the recipient is registered for",
        compute="_compute_l10n_ge_tax_id_custom_domain",
    )

    def _compute_l10n_ge_tax_id_custom_domain(self):
        for line in self:
            categories = line._get_comodel_partner().l10n_ge_wht_category_ids
            if line.country_code != "GE" or not categories:
                line.l10n_ge_tax_id_custom_domain = False
                continue
            domain = self._get_withholding_tax_domain(line.company_id, line.comodel_payment_type)
            line.l10n_ge_tax_id_custom_domain = list(
                domain.map_conditions(lambda condition: (Domain.TRUE if condition.field_expr == "is_withholding_tax" else condition))
                & Domain("l10n_ge_wht_category_ids", "in", categories.ids),
            )
