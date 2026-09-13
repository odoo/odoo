from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    project_id = fields.Many2one(
        comodel_name="project.project",
        domain=[("is_template", "=", False)],
    )
