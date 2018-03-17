# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _
from openerp.exceptions import except_orm


class SchoolMeeting(models.TransientModel):
    _name = "school.meeting"
    meeting_with = fields.Selection([('student', 'Students'),
                                     ('parent', 'Parents'),
                                     ('teacher', 'Teachers')],
                                    'Meeting With',
                                    required=True)
    name = fields.Char('Meeting Subject', size=128, required=True)
    meeting_date = fields.Datetime('Meeting Date and Start Time', required=True)
    deadline = fields.Datetime('Meeting Ends at', required=True)
    description = fields.Text('Description')

    @api.multi
    def set_meeting(self):
        cal_event_obj = self.env['calendar.event']
        attendee_ids = []
        flag = False

        if self.meeting_with == 'student':
            student_obj = self.env['school.student']
            error_student = ''
            for student in student_obj.search([('state', '=', 'admitted')]):
                if not student.email:
                    flag = True
                    error_student += (student.name + " with ID: " + student.pid + "\n")
                else:
                    attendee_ids.append((0, 0, {'user_id': student.user_id.id,
                                                'email': student.email}))
            if flag:
                raise except_orm(_('Error !'),
                                 _('Following Student'
                                   'does not have Email ID.\n\n' + error_student +
                                   '\nMeeting cannot be scheduled.'))
            cal_event_obj.create({'name': self.name,
                                  'start': self.meeting_date,
                                  'stop': self.deadline,
                                  'description': self.description,
                                  'attendee_ids': attendee_ids})
            return {'type': 'ir.actions.act_window_close'}

        elif self.meeting_with == 'parent':
            parent_obj = self.env['school.parent']
            error_parent = ''
            for parent in parent_obj.browse(self._context['active_ids']):
                if not parent.email:
                    flag = True
                    error_parent += (parent.name + "\n")
                else:
                    attendee_ids.append((0, 0, {'user_id': parent.user_id.id,
                                                'email': parent.email}))
            if flag:
                raise except_orm(_('Error !'),
                                 _('Following Parent'
                                   'does not have Email ID.\n\n' + error_parent +
                                   '\nMeeting cannot be scheduled.'))
            cal_event_obj.create({'name': self.name,
                                  'start': self.meeting_date,
                                  'stop': self.deadline,
                                  'description': self.description,
                                  'attendee_ids': attendee_ids})
            return {'type': 'ir.actions.act_window_close'}

        elif self.meeting_with == 'teacher':
            teacher_obj = self.env['hr.employee'].search(['is_school_teacher', "=", True])
            error_teacher = ''
            for teacher in teacher_obj.browse(self._context['active_ids']):
                if not teacher.email:
                    flag = True
                    error_teacher += (teacher.name + "\n")
                else:
                    attendee_ids.append((0, 0, {'user_id': teacher.user_id.id,
                                                'email': teacher.email}))
            if flag:
                raise except_orm(_('Error !'),
                                 _('Following Teacher'
                                   'does not have Email ID.\n\n' + error_teacher +
                                   '\nMeeting cannot be scheduled.'))
            cal_event_obj.create({'name': self.name,
                                  'start': self.meeting_date,
                                  'stop': self.deadline,
                                  'description': self.description,
                                  'attendee_ids': attendee_ids})
            return {'type': 'ir.actions.act_window_close'}
