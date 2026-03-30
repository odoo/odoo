from odoo import fields, models


class ForgeGroup(models.Model):
    _name = "forge.group"
    _description = "Forge Group"

    name = fields.Char(required=True)
    module_id = fields.Many2one("forge.module", required=True, ondelete="cascade")
    implied_ids = fields.Many2many(
        "forge.group",
        "forge_group_implied_rel",
        "group_id",
        "implied_id",
        string="Implied Groups",
    )
