from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_ge_treaty_exempt_amount = fields.Monetary(
        string="Withheld Treaty Exempt",
        currency_field="company_currency_id",
        readonly=True,
        help="Treaty exempt amount of the withholding lines behind this withholding tax journal item,"
        " in company currency and signed like its base amount.",
    )
