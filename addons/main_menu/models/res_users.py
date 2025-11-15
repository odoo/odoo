from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    menu_bookmark_ids = fields.One2many("menu.bookmark", "user_id", "Bookmarks")
