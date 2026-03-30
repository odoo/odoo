from odoo import fields, models


class ForgeModel(models.Model):
    _name = "forge.model"
    _description = "Forge Model"

    name = fields.Char(string="Model Description", required=True)
    technical_name = fields.Char(required=True, help="e.g. kodoo.my.model")
    module_id = fields.Many2one("forge.module", required=True, ondelete="cascade")
    description = fields.Text()

    _sql_constraints = [
        (
            "technical_name_per_module",
            "unique(technical_name, module_id)",
            "...",
        )
    ]
