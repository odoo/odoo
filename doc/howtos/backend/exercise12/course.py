# -*- coding: utf-8 -*-
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

    @api.one
    @api.depends('seats', 'attendee_ids')
    def _taken_seats(self):
        if not self.seats:
            self.seats_taken = 0.0
        else:
            self.seats_taken = 100.0 * len(self.attendee_ids) / self.seats

class Attendee(models.Model):
    _name = 'openacademy.attendee'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner',
        string="Partner", required=True, ondelete='cascade')
    session_id = fields.Many2one('openacademy.session',
        string="Session", required=True, ondelete='cascade')
