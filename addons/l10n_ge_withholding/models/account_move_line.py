from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ge_treaty_exempt_amount = fields.Monetary(
        string="Withheld Treaty Exempt",
        currency_field="company_currency_id",
        readonly=True,
        help="Treaty exempt amount of the withholding lines behind this withholding tax journal item,"
        " in company currency and signed like its base amount.",
    )

    @api.constrains("tax_ids")
    def _check_l10n_ge_gross_withholding_tax_alone(self):
        for line in self:
            withholding_taxes = line.tax_ids.filtered("is_withholding_tax")
            if len(withholding_taxes) > 1 and any(withholding_taxes.mapped("l10n_ge_is_gross")):
                raise ValidationError(self.env._("A gross withholding tax cannot be combined with another withholding tax on the same line."))
