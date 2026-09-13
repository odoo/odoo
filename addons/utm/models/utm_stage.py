from odoo import fields, models


class UtmStage(models.Model):
    """Stage for utm campaigns."""

    _name = "utm.stage"
    _description = "Campaign Stage"
    _order = "sequence"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=1)
