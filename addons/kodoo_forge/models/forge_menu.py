from odoo import fields, models


class ForgeMenu(models.Model):
    _name = "forge.menu"
    _description = "Forge Menu"

    name = fields.Char(required=True)
    module_id = fields.Many2one("forge.module", required=True, ondelete="cascade")
    parent_id = fields.Many2one(
        "forge.menu", ondelete="set null", string="Parent Menu"
    )
    action_id = fields.Many2one("forge.action", ondelete="set null")
    sequence = fields.Integer(default=10)
    web_icon = fields.Char()
