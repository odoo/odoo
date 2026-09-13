from odoo import fields, models


class EventBoothCategory(models.Model):
    _name = "event.booth.category"
    _description = "Event Booth Category"
    _inherit = ["mixin.image"]
    _order = "sequence ASC"

    active = fields.Boolean(default=True)
    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    description = fields.Html(
        translate=True,
        sanitize_attributes=False,
    )
    booth_ids = fields.One2many(
        comodel_name="event.booth",
        inverse_name="booth_category_id",
        string="Booths",
        groups="event.group_event_registration_desk",
    )
