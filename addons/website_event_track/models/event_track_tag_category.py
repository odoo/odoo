from odoo import fields, models


class EventTrackTagCategory(models.Model):
    _name = "event.track.tag.category"
    _description = "Event Track Tag Category"
    _order = "sequence"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    tag_ids = fields.One2many("event.track.tag", "category_id", string="Tags")
