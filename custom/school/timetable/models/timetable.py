# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class TimeTable(models.Model):
    _description = 'Time Table'
    _name = 'time.table'

    name = fields.Char('Description')
    classroom_id = fields.Many2one('school.classroom', 'Form',
                                  required=True,
                                  help="Select Form")
    academic_year_id = fields.Many2one('school.academic.year', 'Year', required=True,
                              help="select academic year")
    timetable_ids = fields.One2many('time.table.line', 'table_id', 'TimeTable')
    timetable_type = fields.Selection([('regular', 'Regular'),
                                       ('exam', 'Exam')],
                                      'Time Table Type', default="regular",
                                      required=True)
    calendar_created = fields.Boolean('Calendar Created', default=False)

    @api.multi
    def create_calendar(self):
        import time
        self.ensure_one()
        calendar_obj = self.env['calendar.event']
        partner_obj = self.env['res.partner']
        for timetable in self.timetable_ids:
            attendee_record = partner_obj.search([('student_id', 'in', [student.id for student in self.classroom_id.student_ids])])
            print attendee_record
            time.sleep(6)
            name = str(timetable.subject_id.name)+" ("+str(timetable.teacher_id.name)+")"
            duration = timetable.duration
            start_datetime = timetable.start_datetime
            stop_datetime = timetable.stop_datetime
            rule_type = 'daily'
            end_type = 'end_date'
            stop_date = self.academic_year_id.date_stop
            teacher_id = timetable.teacher_id.id
            classroom_id = self.classroom_id.id
            calendar_obj.create({
                'name': name,
                'duration': duration,
                'recurrency': True,
                'interval': 7,
                'start_datetime': start_datetime,
                'rrule_type': rule_type,
                'start': start_datetime,
                'stop': stop_datetime,
                'end_type': end_type,
                'final_date': stop_date,
                'teacher_id': teacher_id,
                'classroom_id': classroom_id,
                'partner_ids': attendee_record,
            })
            self.calendar_created = True

    @api.one
    def check_time(self, x, y):
        if ":" in x and ":" in y:
            xa, xb = x.split(":")
            xa, xb = int(xa), int(xb)
            if xa in range(0, 23) and xb in range(0, 59):
                ya, yb = y.split(":")
                ya, yb = int(ya), int(yb)
                if ya in range(0, 23) and yb in range(0, 59):
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False

    @api.multi
    @api.constrains('timetable_ids')
    def _check_lecture(self):
        '''Method to check same lecture is not assigned on same day'''
        if self.timetable_type == 'regular':
            domain = [('table_id', '=', self.id)]
            line_ids = self.env['time.table.line'].search(domain)
            for rec in line_ids:
                records = [rec_check.id for rec_check in line_ids
                           if (rec.week_day == rec_check.week_day and
                               rec.start_time == rec_check.start_time and
                               rec.end_time == rec_check.end_time and
                               rec.teacher_id.id == rec.teacher_id.id)]
                if len(records) > 1:
                    raise ValidationError(_('''You cannot set lecture at same
                                            time %s  at same day %s for teacher
                                            %s..!''') % (rec.start_time,
                                                         rec.week_day,
                                                         rec.teacher_id.name))
                # Checks if time is greater than 24 hours than raise error
                import time
                print self.check_time(rec.start_time, rec.end_time), "Check time"
                time.sleep(5)
                if False in self.check_time(rec.start_time, rec.end_time):
                    raise ValidationError(_('''Start Time and End Should be should be less than
                                            24 hours'''))
            return True


class TimeTableLine(models.Model):
    _description = 'Time Table Line'
    _name = 'time.table.line'
    _rec_name = 'table_id'

    @api.multi
    @api.constrains('teacher_id', 'subject_id')
    def check_teacher(self):
        '''Check if lecture is not related to teacher than raise error'''
        if (self.teacher_id.id not in self.subject_id.teacher_ids.ids and
                self.table_id.timetable_type == 'regular'):
            raise ValidationError(_('The subject %s is not assigned to'
                                    'teacher %s.') % (self.subject_id.name,
                                                      self.teacher_id.name ))

    teacher_id = fields.Many2one('hr.employee', 'Teacher Name',
                                 help="Select Teacher")
    subject_id = fields.Many2one('school.subject', 'Subject Name',
                                 required=True,
                                 help="Select Subject")
    table_id = fields.Many2one('time.table', 'TimeTable')
    start_datetime = fields.Datetime('Initial Date and Time', required=True)
    stop_datetime = fields.Datetime('End Datetime', track_visibility='onchange')
    duration = fields.Float('Duration', required=True)
    start_time = fields.Char('Start Time', required=True,
                              help="Time according to time format of 24 hours", size=5)
    end_time = fields.Char('End Time', required=True,
                            help="Time according to time format of 24 hours", size=5)
    week_day = fields.Selection([('monday', 'Monday'),
                                 ('tuesday', 'Tuesday'),
                                 ('wednesday', 'Wednesday'),
                                 ('thursday', 'Thursday'),
                                 ('friday', 'Friday'),
                                 ('saturday', 'Saturday')], "Week day",)

    @api.onchange('start_datetime', 'duration')
    def _onchange_duration(self):
        if self.start_datetime:
            start = fields.Datetime.from_string(self.start_datetime)
            self.stop_datetime = fields.Datetime.to_string(start + timedelta(hours=self.duration))

    # TODO fix overlapping timetable
    '''
    FIXME fix overlapping timetable
    
    @api.constrains('start_datetime', 'stop_datetime')
    def _check_time_table(self):
        obj_table_lines = self.search(['week_day', '=', self.week_day])
        timeslot_list = []
        for rec_line in obj_table_lines:
            timeslot_list.append(rec_line.id)
        for current_timeslot in self:
            timeslot_list.remove(current_timeslot.id)
            data_table_lines = self.browse(timeslot_list)
            for old_tslot in data_table_lines:
                if old_tslot.start_datetime <= self.start_datetime <= old_tslot.stop_datetime or \
                                        old_tslot.start_datetime <= self.stop_datetime <= old_tslot.stop_datetime:
                    raise Warning(_('Error! You cannot define overlapping TimeTable.'))
        '''


class SubjectSubject(models.Model):
    _inherit = "school.subject"

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False,
                access_rights_uid=None):
        '''Override method to get subject related to teacher'''
        teacher_id = self._context.get('teacher_id')
        if teacher_id:
            for teacher_data in self.env['hr.employee'].browse(teacher_id):
                args.append(('teacher_ids', 'in', [teacher_data.id]))
        return super(SubjectSubject, self)._search(
            args=args, offset=offset, limit=limit, order=order, count=count,
            access_rights_uid=access_rights_uid)


class Meeting(models.Model):
    _inherit = 'calendar.event'
    classroom_id = fields.Many2one('school.classroom', "Form")
    teacher_id = fields.Many2one('hr.employee', "Teacher")
    partner_ids = fields.Many2many('res.partner', 'calendar_event_res_partner_rel', string='Attendees', states={'done': [('readonly', True)]})

