from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

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
    maintenance_profile_id = fields.One2one(
        comodel_name="maintenance.profile",
        inverse_name="resource_id",
    )
