# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventRegistrationAttendance(models.Model):
    """ Represent an attendance for a registration at an event """
    _name = 'event.registration.attendance'
    _description = 'Event Registration Attendance'

    registration_id = fields.Many2one('event.registration', required=True, index=True, ondelete='cascade')
    attendance_date = fields.Datetime(string='Attendance Date')
