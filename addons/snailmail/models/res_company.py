from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    snailmail_color = fields.Boolean(default=True)
    snailmail_cover = fields.Boolean(
        string="Add a Cover Page",
        default=False,
    )
    snailmail_duplex = fields.Boolean(
        string="Both sides",
        default=False,
    )
