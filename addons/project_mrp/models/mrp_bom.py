from odoo import fields, models


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    project_id = fields.Many2one(
        comodel_name="project.project",
        domain=[("is_template", "=", False)],
    )
