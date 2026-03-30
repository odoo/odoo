from odoo import fields, models


class ForgeAction(models.Model):
    _name = "forge.action"
    _description = "Forge Action"

    name = fields.Char(required=True)
    module_id = fields.Many2one("forge.module", required=True, ondelete="cascade")
    model_id = fields.Many2one("forge.model", required=True, ondelete="cascade")
    view_mode = fields.Char(default="list,form")
    domain = fields.Char(default="[]")
    context = fields.Char(default="{}")
