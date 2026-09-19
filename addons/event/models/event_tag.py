from odoo import fields, models


class EventTagCategory(models.Model):
    _name = "event.tag.category"
    _description = "Event Tag Category"
    _order = "sequence"

    def _default_sequence(self):
        """
        Here we use a _default method instead of ordering on 'sequence, id' to
        prevent adding a new related stored field in the 'event.tag' model that
        would hold the category id.
        """
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=_default_sequence)
    tag_ids = fields.One2many(
        comodel_name="event.tag",
        inverse_name="category_id",
        string="Tags",
    )


class EventTag(models.Model):
    _name = "event.tag"
    _inherit = ["mixin.color"]
    _description = "Event Tag"
    _order = "category_sequence, sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=0)
    category_id = fields.Many2one(
        comodel_name="event.tag.category",
        index=True,
        required=True,
        ondelete="cascade",
    )
    category_sequence = fields.Integer(
        related="category_id.sequence",
        string="Category Sequence",
    )
    color = fields.Integer(
        string="Color Index",
        default=lambda self: self._default_color(),
        help="Tag color. No color means no display in kanban or front-end, to distinguish internal tags from public categorization tags.",
    )
