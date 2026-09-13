from odoo import fields, models


class EventTrackTagCategory(models.Model):
    _name = "event.track.tag.category"
    _description = "Event Track Tag Category"
    _order = "sequence"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    tag_ids = fields.One2many(
        comodel_name="event.track.tag",
        inverse_name="category_id",
        string="Tags",
    )
