from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    partnership_label = fields.Char(
        help="Name used to refer to affiliates: partners, members, alumnis, etc...",
        translate=True,
        default=lambda s: s.env._("Members"),
    )
