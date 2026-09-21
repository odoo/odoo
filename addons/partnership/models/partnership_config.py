from odoo import fields, models


class PartnershipConfig(models.Model):
    _name = "partnership.config"
    _description = "A company's partnership configuration"
    _inherit = ["mixin.company.config"]

    partnership_label = fields.Char(
        translate=True,
        default=lambda s: s.env._("Members"),
        help="Name used to refer to affiliates: partners, members, alumnis, etc...",
    )
