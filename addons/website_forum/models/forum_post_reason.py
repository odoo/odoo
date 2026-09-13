from odoo import fields, models


class ForumPostReason(models.Model):
    _name = "forum.post.reason"
    _description = "Post Closing Reason"
    _order = "name"

    name = fields.Char(
        string="Closing Reason",
        translate=True,
        required=True,
    )
    reason_type = fields.Selection(
        selection=[("basic", "Basic"), ("offensive", "Offensive")],
        default="basic",
    )
