from odoo import models, fields


class Tag(models.Model):
    _name = "t9n.tag"
    _description = "Tags to tag the message with."
    _order = "name"

    name = fields.Char(required=True)
    color = fields.Integer()
