from odoo import fields, models

class Recurrence(models.Model):
    _name = 'calendar.recurrence'
    _inherit = 'calendar.recurrence'

    ms_organizer_event_id = fields.Char('Microsoft Calendar Organizer event Id')
    ms_universal_event_id = fields.Char('Microsoft Calendar Universal event Id')
