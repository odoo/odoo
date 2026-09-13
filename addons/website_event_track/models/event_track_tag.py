from odoo import fields, models


class EventTrackTag(models.Model):
    _name = "event.track.tag"
    _inherit = ["mixin.color"]
    _description = "Event Track Tag"
    _order = "category_id, sequence, name"

    name = fields.Char(
        string="Tag Name",
        required=True,
    )
    track_ids = fields.Many2many(
        comodel_name="event.track",
        string="Tracks",
    )
    color = fields.Integer(
        string="Color Index",
        default=lambda self: self._default_color(),
        help="Note that colorless tags won't be available on the website.",
    )
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one(
        comodel_name="event.track.tag.category",
        index="btree_not_null",
        ondelete="set null",
    )

    _name_uniq = models.Constraint(
        "unique (name)",
        "Tag name already exists!",
    )
