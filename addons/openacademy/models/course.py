# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models, fields, api, exceptions, _


class Course(models.Model):
    _name = 'openacademy.course'
    _inherit = 'mail.thread'

    name = fields.Char()
    description = fields.Text()
    responsible_id = fields.Many2one('res.users', ondelete='set null', string="Responsible", index=True)
    session_ids = fields.One2many('openacademy.session', 'course_id', string="Sessions")
    level = fields.Selection([(1, 'Easy'), (2, 'Medium'), (3, 'Hard')], string="Difficulty Level")
    color = fields.Integer()
    session_count = fields.Integer("Session Count", compute="_compute_session_count")

    fname = fields.Char('Filename')
    datas = fields.Binary('File')
    currency_id = fields.Many2one('res.currency', 'Currency')

    price = fields.Float('Price')

    _sql_constraints = [
       ('name_description_check', 'CHECK(name != description)',
        _("The title of the course should not be the description")),

       ('name_unique', 'UNIQUE(name)',
        _("The course title must be unique")),
    ]

    @api.multi
    def copy(self, default=None):
        default = dict(default or {})

        copied_count = self.search_count(
            [('name', '=like', _(u"Copy of {}%".format(self.name)))])
        if not copied_count:
            new_name = _(u"Copy of {}").format(self.name)
        else:
            new_name = _(u"Copy of {} ({})").format(self.name, copied_count)

        default['name'] = new_name
        return super(Course, self).copy(default)

    @api.depends('session_ids')
    def _compute_session_count(self):
        for course in self:
            course.session_count = len(course.session_ids)


class Session(models.Model):
    _name = 'openacademy.session'
    _order = 'name'

    name = fields.Char(required=True)
    start_date = fields.Date(default=lambda self : fields.Date.today())
    end_date = fields.Date(string='End date', store=True, compute='_get_end_date', inverse='_set_end_date')
    active = fields.Boolean(default=True)
    duration = fields.Float(digits=(6, 2), help="Duration in days", default=1)
    seats = fields.Integer(string="Number of seats")
    instructor_id = fields.Many2one('res.partner', string="Instructor") #No ondelete = set null
    course_id = fields.Many2one('openacademy.course', ondelete='cascade', string="Course", required=True)
    attendee_ids = fields.Many2many('res.partner', string="Attendees", domain=[('is_company', '=', False)])
    taken_seats = fields.Float(string="Taken seats", compute='_taken_seats')
    level = fields.Selection(related='course_id.level', readonly=True)
    responsible_id = fields.Many2one(related='course_id.responsible_id', readonly=True, store=True)
    description = fields.Html()

    percentage_per_day = fields.Integer("%", default=100)
    attendees_count = fields.Integer(string="Attendees count", compute='_get_attendees_count', store=True)
    color = fields.Integer()

    sequence = fields.Integer('sequence')

    state = fields.Selection([
                    ('draft', "Draft"),
                    ('confirmed', "Confirmed"),
                    ('done', "Done"),
                    ], default='draft')

    is_paid = fields.Boolean('Is paid')

    def _warning(self, title, message):
        return {
          'warning': {
            'title': title,
            'message': message,
          },
        }

    @api.depends('seats', 'attendee_ids')
    def _taken_seats(self):
        for session in self:
            if not session.seats:
                session.taken_seats = 0.0
            else:
                session.taken_seats = 100.0 * len(session.attendee_ids) / session.seats

    @api.depends('attendee_ids')
    def _get_attendees_count(self):
        for session in self:
            session.attendees_count = len(session.attendee_ids)

    @api.onchange('seats', 'attendee_ids')
    def _verify_valid_seats(self):
        if self.seats < 0:
            return self._warning(_("Incorrect 'seats' value"), _("The number of available seats may not be negative"))
        if self.seats < len(self.attendee_ids):
            return self._warning(_("Too many attendees"), _("Increase seats or remove excess attendees"))

    @api.constrains('instructor_id', 'attendee_ids')
    def _check_instructor_not_in_attendees(self):
        for session in self:
            if session.instructor_id and session.instructor_id in session.attendee_ids:
                raise exceptions.ValidationError("A session's instructor can't be an attendee")

    @api.depends('start_date', 'duration')
    def _get_end_date(self):
        for session in self:
            if not (session.start_date and session.duration):
                session.end_date = session.start_date
            else:
                # Add duration to start_date, but: Monday + 5 days = Saturday, so
                # subtract one second to get on Friday instead
                start = fields.Datetime.from_string(session.start_date)
                duration = timedelta(days=session.duration, seconds=-1)
                session.end_date = start + duration

    def _set_end_date(self):
        for session in self:
            if session.start_date and session.end_date:
                # Compute the difference between dates, but: Friday - Monday = 4 days,
                # so add one day to get 5 days instead
                start_date = fields.Datetime.from_string(session.start_date)
                end_date = fields.Datetime.from_string(session.end_date)
                session.duration = (end_date - start_date).days + 1

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})

    def _auto_transition(self):
        # Don't use this in production; it may have bad performance
        for session in self:
            if session.taken_seats >= 50.0 and session.state == 'draft':
                session.state = 'confirmed'

    @api.multi
    def write(self, vals):
        res = super(Session, self).write(vals)
        self._auto_transition()
        return res

    @api.model
    def create(self, vals):
        rec = super(Session, self).create(vals)
        rec._auto_transition()
        return rec
