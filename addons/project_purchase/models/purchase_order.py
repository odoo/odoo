from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    project_id = fields.Many2one(
        comodel_name="project.project",
        domain=[("is_template", "=", False)],
    )
