# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
import datetime as datetimee
import requests
from odoo import models, fields, api, exceptions, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class SchoolAttendance(models.Model):
    _name = "school.attendance"
    _description = "Attendance"
    _order = "check_in desc"

    @api.model
    def create(self, vals):
        late_time = self.env.user.company_id.late_time
        student = self.env['school.student'].search([('id', '=', vals['student_id'])])
        form_id = self.env['school.form'].search([('id', '=', student.form_id.id)]).id or False
        classroom_id = self.env['school.classroom'].search([('id', '=', student.classroom_id.id)]).id or False
        class_id = self.env['school.class'].search([('id', '=', student.class_id.id)]).id or False
        a, b = vals['check_in'].split(" ")
        x, y, z = b.split(":")
        time_in = float(x+"."+y)
        if time_in > late_time:
            vals['late'] = True
        vals['form_id'] = form_id
        vals['classroom_id'] = classroom_id
        vals['class_id'] = class_id
        result = super(SchoolAttendance, self).create(vals)
        self.send_login_notification(student, 'in', b)
        result.signin_reminder_sent = True
        return result

    # TODO Look at this again
    '''
    @api.one
    def has_internet(self):
        try:
            urllib2.urlopen('http://216.58.192.142', timeout=1)
            return True
        except urllib2.URLError as err:
            return False
    '''

    def send_login_notification(self, student, type, time):
        if student.parent_id.phone:
            api_key = self.env['ir.config_parameter'].get_param('sms.api_key')
            api_secret = self.env['ir.config_parameter'].get_param('sms.api_secret')
            name = str(student.name)
            to = str(student.parent_id.phone)
            sender = str(self.env.user.company_id.name)
            in_message = "Hello, your child/ward %s has just signed in at school at %s" % (name, time)
            out_message = "Hello, your child/ward %s has just signed out of school at %s" % (name, time)

            if type == 'in':
                post_data = {'api_key': api_key, 'api_secret': api_secret, 'to': to, 'from': sender,
                             'text': in_message
                             }
                requests.post('https://rest.nexmo.com/sms/json', data=post_data)
                return True
            if type == 'out':
                post_data = {'api_key': 'c792df8e', 'api_secret': '3aa3d7631723d42a', 'to': to, 'from': sender,
                             'text': out_message
                             }
                requests.post('https://rest.nexmo.com/sms/json', data=post_data)
                return True

    def cron_send_attendance_notification(self):
        attendances = self.env['school.attendance'].search([('date', '=', date.today()),
                                                           ('signin_reminder_sent', '=', True),
                                                           ('signout_reminder_sent', '=', False)])
        for attendance in attendances:
            if attendance.check_out:
                a, b = attendance.check_out.split(" ")
                attendance.send_login_notification(attendance.student_id, 'out', b)
                attendance.signout_reminder_sent = True

    def cron_no_sign_out(self):
        attendances = self.search([('check_out', '=', False)])
        for attendance in attendances:
            if datetime.strptime(attendance.check_in.split(" ")[0], '%Y-%m-%d').date() < datetimee.date.today():
                attendance.student_id.attendance_state = 'waiting'

    def _default_student(self):
        return self.env['school.student'].search([('user_id', '=', self.env.uid)], limit=1)

    student_id = fields.Many2one('school.student', string="Student", default=_default_student, required=True, ondelete='cascade', index=True)
    form_id = fields.Many2one('school.form', string="Form")
    class_id = fields.Many2one('school.class', string="Class")
    classroom_id = fields.Many2one('school.classroom', string="Classroom")
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=True)
    date = fields.Date('Date', default=date.today())
    check_out = fields.Datetime(string="Check Out")
    attendance_code = fields.Char('Attendance Code', compute='_compute_att_code', help='Attendance Code', store=True, readonly=True)
    time_spent = fields.Float(string='Time Spent in School', compute='_compute_time_spent', store=True, readonly=True)
    signin_reminder_sent = fields.Boolean('Sign in Reminder Sent', default=False)
    signout_reminder_sent = fields.Boolean('Sign out Reminder Sent', default=False)
    late = fields.Boolean('Late', default=False)
    school_type = fields.Selection([('primary', 'Primary'),
                                    ('secondary', 'Secondary')],
                                   default=lambda obj: obj.env.user.company_id.school_type,
                                   required=True,
                                   readonly=True
                                   )

    _sql_constraints = [
        ('attendance_code_unique',
         'unique(attendance_code)',
         'Error! This student already has an attendance record  for today!')
    ]

    @api.depends('student_id')
    def _compute_att_code(self):
        self.attendance_code = str(self.student_id.pid)+str(self.check_in.split(" ")[0])

    @api.multi
    def name_get(self):
        result = []
        for attendance in self:
            if not attendance.check_out:
                result.append((self.id, _("%(stu_name)s from %(check_in)s") % {
                    'stu_name': self.student_id.name,
                    'check_in': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.check_in))),
                }))
            else:
                result.append((self.id, _("%(stu_name)s from %(check_in)s to %(check_out)s") % {
                    'stu_name': self.student_id.name,
                    'check_in': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.check_in))),
                    'check_out': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(self.check_out))),
                }))
        return result

    @api.depends('check_in', 'check_out')
    def _compute_time_spent(self):
        for attendance in self:
            if attendance.check_out:
                delta = datetime.strptime(attendance.check_out, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.strptime(
                    attendance.check_in, DEFAULT_SERVER_DATETIME_FORMAT)
                attendance.time_spent = delta.total_seconds() / 3600.0

    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ verifies if check_in is earlier than check_out. """
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                if attendance.check_out < attendance.check_in:
                    raise exceptions.ValidationError(_('"Check Out" time cannot be earlier than "Check In" time.'))

    @api.constrains('check_in', 'check_out', 'student_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same Student.
            For the same Student we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous student records
        """
        for attendance in self:
            # we take the latest attendance before our check_in time and check it doesn't overlap with ours
            last_attendance_before_check_in = self.env['school.attendance'].search([
                ('student_id', '=', attendance.student_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out >= attendance.check_in:
                raise exceptions.ValidationError(_(" Error!! Cannot create new attendance record for %(stu_name)s, the student was already checked in on %(datetime)s") % {
                    'stu_name': attendance.student_id.name,
                    'datetime': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(attendance.check_in))),
                })
            if last_attendance_before_check_in.attendance_code == self.attendance_code:
                raise exceptions.ValidationError(_(
                    "Error!! Cannot create new attendance record for %(stu_name)s, the student already HAS AN ATTENDANCE record for the selected day ") % {
                                                     'stu_name': attendance.student_id.name,})
            if datetime.strptime(attendance.check_in.split(" ")[0], '%Y-%m-%d').date() > datetimee.date.today():
                raise exceptions.ValidationError(_(
                    "Error! Cannot create future attendance record for %(stu_name)s,") % {
                                                     'stu_name': attendance.student_id.name, })

            if not attendance.check_out:
                # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                no_check_out_attendances = self.env['school.attendance'].search([
                    ('student_id', '=', attendance.student_id.id),
                    ('check_out', '=', False),
                    ('id', '!=', attendance.id),
                ])
                if no_check_out_attendances:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(stu_name)s, the student hasn't checked out since %(datetime)s") % {
                        'stu_name': attendance.student_id.name,
                        'datetime': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(no_check_out_attendances.check_in))),
                    })
            else:
                # we verify that the latest attendance with check_in time before our check_out time
                # is the same as the one before our check_in time computed before, otherwise it overlaps
                last_attendance_before_check_out = self.env['school.attendance'].search([
                    ('student_id', '=', attendance.student_id.id),
                    ('check_in', '<=', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(stu_name)s, the student was already checked in on %(datetime)s") % {
                        'stu_name': attendance.student_id.name,
                        'datetime': fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(last_attendance_before_check_out.check_in))),
                    })

    @api.multi
    def copy(self):
        raise exceptions.UserError(_('You cannot duplicate an attendance.'))
