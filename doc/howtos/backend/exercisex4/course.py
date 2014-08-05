# -*- coding: utf-8 -*-
from datetime import date, timedelta

import openerp.tools
from openerp import api, fields, models

class Course(models.Model):
    _name = 'openacademy.course'

    name = fields.Char(string="Title", required=True)
    description = fields.Text()

    responsible_id = fields.Many2one('res.users',
        ondelete='set null', string="Responsible", index=True)
    session_ids = fields.One2many(
        'openacademy.session', 'course_id', string="Session")

class Session(models.Model):
    _name = 'openacademy.session'

    name = fields.Char(required=True)
    start_date = fields.Date()
    duration = fields.Float(digits=(6, 2), help="Duration in days")
    seats = fields.Integer(string="Number of seats")

    instructor_id = fields.Many2one('res.partner', string="Instructor")
    course_id = fields.Many2one('openacademy.course',
        ondelete='cascade', string="Course", required=True)
    attendee_ids = fields.One2many(
        'openacademy.attendee', 'session_id', string="Attendees")

    seats_taken = fields.Float(string="Taken seats", compute='_taken_seats')
    end_date = fields.Date(
        string="End Date", compute='_get_end_date', inverse='_set_end_date')

    hours = fields.Float(
        string="Duration in hours", compute='_get_hours', inverse='_set_hours')

    @api.one
    @api.depends('seats', 'attendee_ids')
    def _taken_seats(self):
        if not self.seats:
            self.seats_taken = 0.0
        else:
            self.seats_taken = 100.0 * len(self.attendee_ids) / self.seats

    @api.one
    @api.depends('start_date', 'duration')
    def _get_end_date(self):
        if not (self.start_date and self.duration):
            self.end_date = self.start_date
            return

        start = date.strptime(
            self.start_date, openerp.tools.DEFAULT_SERVER_DATE_FORMAT)
        duration = timedelta(days=self.duration)

        self.end_date = (start + duration).strftime(openerp.tools.DEFAULT_SERVER_DATE_FORMAT)

    @api.one
    def _set_end_date(self):
        if not (self.start_date and self.end_date):
            return

        start_date = date.strptime(self.start_date, openerp.tools.DEFAULT_SERVER_DATE_FORMAT)
        end_date = date.strptime(self.end_date, openerp.tools.DEFAULT_SERVER_DATE_FORMAT)

        self.duration = end_date - start_date

    @api.one
    @api.depends('duration')
    def _get_hours(self):
        self.hours = self.duration * 24

    @api.one
    def _set_hours(self):
        self.duration = self.hours / 24

class Attendee(models.Model):
    _name = 'openacademy.attendee'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner',
        string="Partner", required=True, ondelete='cascade')
    session_id = fields.Many2one('openacademy.session',
        string="Session", required=True, ondelete='cascade')
