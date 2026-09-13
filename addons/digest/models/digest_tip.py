from odoo import fields, models
from odoo.tools.translate import html_translate


class DigestTip(models.Model):
    """Rotating usage tip shown in the digest email."""

    _name = "digest.tip"
    _description = "Digest Tips"
    _order = "sequence"

    sequence = fields.Integer(
        default=1,
        help="Used to display digest tip in email template base on order",
    )
    name = fields.Char(translate=True)
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Recipients",
        help="Users having already received this tip",
    )
    tip_description = fields.Html(
        string="Tip description",
        translate=html_translate,
        sanitize=False,
    )
    group_id = fields.Many2one(
        comodel_name="res.groups",
        string="Authorized Group",
        default=lambda self: self.env.ref("base.group_user"),
    )
