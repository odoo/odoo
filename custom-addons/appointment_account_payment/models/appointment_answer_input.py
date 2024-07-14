# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AppointmentAnswerInput(models.Model):
    _inherit = "appointment.answer.input"

    # Answers not linked to a calendar event are unlinked in calendar.booking unlink method.
    calendar_booking_id = fields.Many2one("calendar.booking", "Meeting Booking")
    calendar_event_id = fields.Many2one(required=False)

    _sql_constraints = [
        ('check_event_or_booking',
         'CHECK(calendar_booking_id IS NOT NULL OR calendar_event_id IS NOT NULL)',
         'The answer inputs must be linked to a meeting or to a booking')
    ]
