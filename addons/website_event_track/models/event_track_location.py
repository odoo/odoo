from odoo import fields, models


class EventTrackLocation(models.Model):
    _name = "event.track.location"
    _description = "Event Track Location"
    _order = "sequence, id"

    name = fields.Char(
        string="Location",
        required=True,
    )
    sequence = fields.Integer(
        default=10,
        help='Define the order in which the location will appear on "Agenda" page',
    )
