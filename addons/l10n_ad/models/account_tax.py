# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ad_exempt_reason = fields.Selection(
        selection=[
            ("E1", "No exempt"),
        ],
        string="Exempt Reason (Andorra)",
    )
    l10n_ad_type = fields.Selection(
        selection=[
            ("subjecte", "Subjecte"),
            ("retencio", "Retenció"),
        ],
        string="Tax Type (Andorra)", default="subjecte",
    )
    l10n_ad_bien_inversion = fields.Boolean(string="Investment Goods (Andorra)",
                                            default=False)
