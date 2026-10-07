# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ad_exempt_reason = fields.Selection(
        selection=[
            # There are others, but they are not supported by this module yet,
            # thus this is kept as a selection field instead of a toggle.
            ("E1", "Not exempt"),
        ],
        string="Exempt Reason (Andorra)",
    )
    l10n_ad_type = fields.Selection(
        selection=[
            ("subjecte", "Subject"),
            ("retencio", "Withholding"),
        ],
        string="Tax Type (Andorra)", default="subjecte",
    )
    l10n_ad_bien_inversion = fields.Boolean(string="Investment Goods (Andorra)")
