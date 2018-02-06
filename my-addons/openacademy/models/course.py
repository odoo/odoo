# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Course(models.Model):
    _name = 'openacademy.course'

    name = fields.Char(name='Title', required=True)
    description = fields.Text()
    responsible_id = fields.Many2one('res.users', ondelete='set null', string="Responsible", index=True)
    session_ids = fields.One2many('openacademy.session', 'course_id', string="Sessions")
    level = fields.Selection([(1, 'Easy'), (2, 'Medium'), (3, 'Hard')], string="Difficulty Level")
    session_count = fields.Integer("Session Count", compute="_compute_session_count")
    theme_ids = fields.Many2many('openacademy.theme', string='Themes')

    _sql_constraints = [
       ('name_description_check', 'CHECK(name != description)',
        "The title of the course should not be the description"),

       ('name_unique', 'UNIQUE(name)',
        "The course title must be unique"),
    ]

    @api.multi
    def copy(self, default=None):
        default = dict(default or {})

        copied_count = self.search_count(
            [('name', '=like', u"Copy of {}%".format(self.name))])
        if not copied_count:
            new_name = u"Copy of {}".format(self.name)
        else:
            new_name = u"Copy of {} ({})".format(self.name, copied_count)

        default['name'] = new_name
        return super(Course, self).copy(default)

    @api.depends('session_ids')
    def _compute_session_count(self):
        for course in self:
            course.session_count = len(course.session_ids)


class Theme(models.Model):
    _name = 'openacademy.theme'

    name = fields.Char(required=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Theme name already exists !"),
    ]


class Session(models.Model):
    _name = 'openacademy.session'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True)
    start_date = fields.Date(default=lambda self : fields.Date.today())
    #end_date = fields.Date(default=lambda self : fields.Date.today())
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

    percentage_per_day = fields.Integer("%", default=100)
    attendees_count = fields.Integer(string="Attendees count", compute='_get_attendees_count', store=True)
    state = fields.Selection([
                    ('draft', "Draft"),
                    ('confirmed', "Confirmed"),
                    ('done', "Done"),
                    ], default='draft')

    attendee_feedback_ids = fields.One2many(
        comodel_name='openacademy.feedback',
        inverse_name='session_id',
        string='Attendees Feedback'
    )

    def _warning(self, title, message):
        return {'warning': {
            'title': title,
            'message': message,
        }}

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
            return self._warning("Incorrect 'seats' value",  "The number of available seats may not be negative")
        if self.seats < len(self.attendee_ids):
            return self._warning("Too many attendees", "Increase seats or remove excess attendees")

    @api.constrains('instructor_id', 'attendee_ids')
    def _check_instructor_not_in_attendees(self):
        for session in self:
            if session.instructor_id and session.instructor_id in session.attendee_ids:
                raise ValidationError("A session's instructor can't be an attendee")

    @api.depends('start_date', 'duration')
    def _get_end_date(self):
        for session in self:
            if not (session.start_date and session.duration):
                session.end_date = session.start_date
            else:
                # Add duration to start_date, but: Monday + 5 days = Saturday,
                # so subtract one second to get on Friday instead
                start = fields.Datetime.from_string(session.start_date)
                duration = timedelta(days=session.duration, seconds=-1)
                session.end_date = start + duration

    def _set_end_date(self):
        for session in self:
            if session.start_date and session.end_date:
                # Compute the difference between dates, but: Friday - Monday = 4
                # days, so add one day to get 5 days instead
                start_date = fields.Datetime.from_string(session.start_date)
                end_date = fields.Datetime.from_string(session.end_date)
                session.duration = (end_date - start_date).days + 1

    @api.multi
    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
            rec.message_post(body="Session %s of the course %s reset to draft" % (rec.name, rec.course_id.name))

    @api.multi
    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'
            rec.message_post(body="Session %s of the course %s confirmed" % (rec.name, rec.course_id.name))

    @api.multi
    def action_done(self):
        for rec in self:
            rec.state = 'done'
            rec.message_post(body="Session %s of the course %s done" % (rec.name, rec.course_id.name))

    def _auto_transition(self):
        for rec in self:
            if rec.taken_seats >= 50.0 and rec.state == 'draft':
                rec.action_confirm()

    @api.multi
    def write(self, vals):
        res = super(Session, self).write(vals)
        for rec in self:
            rec._auto_transition()
        if vals.get('instructor_id'):
            self.message_subscribe([vals['instructor_id']])
        return res

    @api.model
    def create(self, vals):
        res = super(Session, self).create(vals)
        res._auto_transition()
        if vals.get('instructor_id'):
            res.message_subscribe([vals['instructor_id']])
        return res

    # Used only on 2nd extra task
    def open_attendees(self):
        self.ensure_one()

        attendees_tree_view = self.env.ref('ex01.attendees_tree_view')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Attendees',
            'res_model': 'res.partner',
            'views': [
                (attendees_tree_view.id, 'tree'),
                (False, 'form')
            ],
            'domain': [('id', 'in', self.attendee_ids.ids)],
        }

    # Used only on 3th extra task
    def action_set_no_of_seats(self, value):
        return self.write({'seats': value})


class Feedback(models.Model):
    _name = 'openacademy.feedback'

    session_id = fields.Many2one('openacademy.session', string="Session", required=True)
    attendee_id = fields.Many2one('res.partner', string='Attendee', required=True)
    session_feedback = fields.Text(string='Feedback')

    _sql_constraints = [(
        'session_attendee_unique',
        'UNIQUE(session_id, attendee_id)',
        "An attendee can only give a feedback once per session"
    )]
