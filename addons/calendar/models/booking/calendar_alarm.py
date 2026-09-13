from odoo import fields, models


class CalendarAlarm(models.Model):
    _inherit = "calendar.alarm"

    default_for_new_appointment_type = fields.Boolean(
        string="New Appointments Default",
        help="Use as default for new Appointment Types",
    )
