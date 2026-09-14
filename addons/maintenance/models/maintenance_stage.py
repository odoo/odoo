from odoo import fields, models


class MaintenanceStage(models.Model):
    """Model for case stages. This models the main stages of a Maintenance Request management flow."""

    _name = "maintenance.stage"
    _description = "Maintenance Stage"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=20)
    fold = fields.Boolean(string="Folded in Maintenance Pipe")
    done = fields.Boolean(string="Request Done")
