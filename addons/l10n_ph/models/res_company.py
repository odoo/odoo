from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    branch_code = fields.Char(
        related="partner_id.branch_code",
        string="Company Branch Code",
    )
    l10n_ph_rdo = fields.Char(
        related="partner_id.l10n_ph_rdo",
        readonly=False,
    )
