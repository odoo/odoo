from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    gov_public_accounting_enabled = fields.Boolean(
        string="GOV Public Accounting",
        help=(
            "Enable public-accounting controls for this company. "
            "When disabled, corporate accounting remains the default behavior."
        ),
        default=False,
    )
