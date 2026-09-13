from odoo import fields, models


class EventTrackVisitor(models.Model):
    _inherit = "event.track.visitor"

    quiz_completed = fields.Boolean("Completed")
    quiz_points = fields.Integer(default=0)
