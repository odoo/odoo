from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    appointment_resource_ids = fields.One2many(
        comodel_name="appointment.resource",
        inverse_name="resource_id",
        export_string_translation=False,
    )
