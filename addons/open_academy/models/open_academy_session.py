# -*- coding: utf-8 -*-
###############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Dhanya Babu (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###############################################################################
from datetime import timedelta
from odoo import api, exceptions, fields, models, _


class OpenAcademySession(models.Model):
    """creating sessions"""
    _name = 'openacademy.session'
    _description = "OpenAcademy Sessions"

    name = fields.Char(string='Name', required=True,
                       help='Name of the session')
    start_date = fields.Date(string='Start Date', default=fields.Date.today(),
                             help='Start date of the session')
    duration = fields.Float(string='Duration', digits=(6, 2),
                            help="Duration in days")
    seats = fields.Integer(string="Number of seats", help='Total seats')
    instructor_id = fields.Many2one('res.partner', string='Instructor',
                                    help='Instructor name')
    course_id = fields.Many2one('openacademy.course', string='Course',
                                ondelete='cascade', required=True,
                                help='Course name')
    attendee_ids = fields.Many2many('res.partner', string="Attendees",
                                    help='Attendees')
    active = fields.Boolean(string='Active', default=True,
                            help='Check this box to indicate if'
                                 ' the session is currently active.')
    taken_seats = fields.Float(string="Taken seats",
                               compute='_compute_taken_seats',
                               help='Taken seats')
    end_date = fields.Date(string="End Date", store=True,
                           compute='_compute_get_end_date',
                           inverse='_compute_set_end_date', help='End date')
    attendees_count = fields.Integer(
        string="Attendees count", compute='_compute_attendees_count',
        store=True, help='Attendees count')
    color = fields.Integer(string='Colour', help='Colour')

    @api.depends('seats', 'attendee_ids')
    def _compute_taken_seats(self):
        """Computing number of seats"""
        for record in self:
            if not record.seats:
                record.taken_seats = 0.0
            else:
                record.taken_seats = 100.0 * len(
                    record.attendee_ids) / record.seats

    @api.onchange('seats', 'attendee_ids')
    def _onchange_seats(self):
        """verifying number of seats
         If number of seats less than zero it will display warning"""
        if self.seats < 0:
            return {
                'warning': {
                    'title': _("Incorrect 'seats' value"),
                    'message': _(
                        "The number of available seats may not be negative"),
                },
            }
        if self.seats < len(self.attendee_ids):
            return {
                'warning': {
                    'title': "Too many attendees",
                    'message': "Increase seats or remove excess attendees",
                },
            }

    def _compute_get_end_date(self):
        """compute the value of end_date based on the values of
          start_date and duration"""
        for record in self:
            if not (record.start_date and record.duration):
                record.end_date = record.start_date
                continue
            # Add duration to start_date, but: Monday + 5 days = Saturday, so
            # subtract one second to get on Friday instead
            duration = timedelta(days=record.duration, seconds=-1)
            record.end_date = record.start_date + duration

    def _compute_set_end_date(self):
        """compute the value of duration  """
        for record in self:
            if not (record.start_date and record.end_date):
                continue
            # Compute the difference between dates,
            # but: Friday - Monday = 4 days,
            # so add one day to get 5 days instead
            record.duration = (record.end_date - record.start_date).days + 1

    @api.depends('attendee_ids')
    def _compute_attendees_count(self):
        """compute number of attendees"""
        for record in self:
            record.attendees_count = len(record.attendee_ids)

    @api.constrains('instructor_id', 'attendee_ids')
    def _check_instructor_not_in_attendees(self):
        """Check instructor is in attendee"""
        for record in self:
            if record.instructor_id and record.instructor_id in record.attendee_ids:
                raise exceptions.ValidationError(
                    "A session's instructor can't be an attendee")
