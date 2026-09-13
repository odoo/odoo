from odoo import fields, models


class EventType(models.Model):
    _inherit = "event.type"

    event_type_booth_ids = fields.One2many(
        comodel_name="event.type.booth",
        inverse_name="event_type_id",
        string="Booths",
        store=True,
        readonly=False,
    )
