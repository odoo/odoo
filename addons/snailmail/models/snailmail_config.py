from odoo import fields, models


class SnailmailConfig(models.Model):
    _name = "snailmail.config"
    _description = "A company's snailmail configuration"
    _inherit = ["mixin.company.config"]

    snailmail_color = fields.Boolean(default=True)
    snailmail_cover = fields.Boolean(
        string="Add a Cover Page",
        default=False,
    )
    snailmail_duplex = fields.Boolean(
        string="Both sides",
        default=False,
    )
