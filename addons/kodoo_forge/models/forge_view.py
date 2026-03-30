from odoo import fields, models


class ForgeView(models.Model):
    _name = "forge.view"
    _description = "Forge View"

    name = fields.Char(required=True)
    view_type = fields.Selection(
        [
            ("form", "Form"),
            ("tree", "Tree"),
            ("list", "List"),
            ("kanban", "Kanban"),
            ("search", "Search"),
            ("pivot", "Pivot"),
            ("graph", "Graph"),
        ],
        required=True,
    )
    model_id = fields.Many2one("forge.model", required=True, ondelete="cascade")
    arch_base = fields.Text(help="XML architecture — generated or manual")
    priority = fields.Integer(default=16)
