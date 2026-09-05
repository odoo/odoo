from odoo import fields, models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    google_resources = fields.Char("Google Resources")
