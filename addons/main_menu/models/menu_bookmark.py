from odoo import fields, models


class MenuBookmark(models.Model):
    _name = "menu.bookmark"
    _description = "Bookmark"
    _order = "sequence, name"

    name = fields.Char(required=True)
    url = fields.Char(string="URL", required=True)
    target = fields.Selection([("_self", "Current Tab"), ("_blank", "New Tab")], default="_self", required=True)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    sequence = fields.Integer()
