from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_bg_branch_code = fields.Char(
        default="0000",
        size=4,
        help="The branch code of the company, if it's a branch.",
    )
