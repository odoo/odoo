from odoo import fields, models


class ResourceResource(models.Model):
    _name = "resource.resource"
    _inherit = ["resource.resource", "mixin.maintenance"]

    maintenance_ids = fields.Many2many(
        comodel_name="maintenance.order",
        relation="maintenance_order_resource_rel",
        column1="resource_id",
        column2="order_id",
    )
    maintenance_plan_ids = fields.Many2many(
        comodel_name="maintenance.plan",
        relation="maintenance_plan_resource_rel",
        column1="resource_id",
        column2="plan_id",
    )
    maintenance_plan_count = fields.Count(count_of="maintenance_plan_ids")
