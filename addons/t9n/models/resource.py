from odoo import fields, models


class Resource(models.Model):
    _name = "t9n.resource"
    _description = "Resource file"

    message_ids = fields.One2many(
        comodel_name="t9n.message",
        inverse_name="resource_id",
        string="Entries to translate",
    )
    project_id = fields.Many2one(
        comodel_name="t9n.project",
    )
