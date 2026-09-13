from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    partnership_label = fields.Char(
        translate=True,
        default=lambda s: s.env._("Members"),
        help="Name used to refer to affiliates: partners, members, alumnis, etc...",
    )
