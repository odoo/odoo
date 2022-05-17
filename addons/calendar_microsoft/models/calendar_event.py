from odoo import fields, models

class Event(models.Model):
    _name = 'calendar.event'
    _inherit = 'calendar.event'

    ms_organizer_event_id = fields.Char('Microsoft Calendar Organizer event Id')
    ms_universal_event_id = fields.Char('Microsoft Calendar Universal event Id')
