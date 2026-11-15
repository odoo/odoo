from odoo import fields, models


class Od19RecognitionBadge(models.Model):
    _name = "od19.recognition.badge"
    _description = "Recognition Badge"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    icon = fields.Char(
        default="fa-star", help="Font Awesome class, e.g. fa-handshake-o"
    )
    color = fields.Char(default="#9E2424")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
