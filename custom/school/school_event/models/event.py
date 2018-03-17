# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from odoo import models, fields, api, _
from odoo.exceptions import Warning as UserError


class SchoolStandard(models.Model):
    _name = 'school.standard'
    _inherit = 'school.standard'
    _rec_name = 'event_ids'

    event_ids = fields.Many2many('school.event', 'school_standard_event_rel',
                                 'event_id', 'standard_id', 'Events')


class SchoolEventParameter(models.Model):
    '''for event parameter based on which score will given'''
    _name = 'school.event.parameter'
    _description = 'Event Parameter'

    name = fields.Char('Parameter Name', required=True)


class SchoolEventParticipant(models.Model):
    '''for Participant which are participated in events'''
    _name = 'school.event.participant'
    _description = 'Participant Information'
    _rec_name = "stu_pid"
    _order = "sequence"

    name = fields.Many2one('student.student', 'Participant Name',
                           readonly=True,
                           help="Name of Student")
    score = fields.Float('Score', default=0,
                         help="Score obtained by student")
    event_id = fields.Many2one('school.event', 'Event', readonly=True,
                               help="Name of event")
    stu_pid = fields.Char('Personal Identification Number', required=True,
                          readonly=True)
    win_parameter_id = fields.Many2one('school.event.parameter', 'Parameter',
                                       readonly=True)
    sequence = fields.Integer('Rank', help="The sequence field is used to Give\
                               Rank to the Participant", default=0)


class SchoolEvent(models.Model):
    '''for events'''
    _name = 'school.event'
    _description = 'Event Information'
    _rec_name = 'name'

    @api.depends('part_ids')
    def _compute_participants(self):
        '''Method to calculate number of participant'''
        for rec in self:
            rec.participants = len(rec.part_ids)

    name = fields.Char('Event Name', help="Full Name of the event")
    event_type = fields.Selection([('intra', 'IntraSchool'),
                                  ('inter', 'InterSchool')],
                                  'Event Type',
                                  help='Event is either IntraSchool\
                                        or InterSchool')
    start_date = fields.Date('Start Date', help="Event Starting Date")
    end_date = fields.Date('End Date', help="Event Ending Date")
    start_reg_date = fields.Date('Start Registration Date',
                                 help="Event registration starting date")
    last_reg_date = fields.Date('Last Registration Date',
                                help="Last Date of registration")
    contact_per_id = fields.Many2one('hr.employee', 'Contact Person',
                                     help="Event contact person")
    supervisor_id = fields.Many2one('hr.employee', 'Supervisor',
                                    help="Event Supervisor Name")
    parameter_id = fields.Many2one('school.event.parameter', 'Parameter',
                                   help="Parameters of the Event\
                                         like (Goal, Point)")
    maximum_participants = fields.Integer('Maximum Participants',
                                          help='Maximum Participant\
                                                of the Event')
    participants = fields.Integer(compute='_compute_participants',
                                  string='Participants', readonly=True)
    part_standard_ids = fields.Many2many('school.standard',
                                         'school_standard_event_rel',
                                         'standard_id', 'event_id',
                                         'Participant Standards',
                                         help="The Participant is from\
                                               which standard")
    state = fields.Selection([('draft', 'Draft'), ('open', 'Running'),
                              ('close', 'Close'), ('cancel', 'Cancel')],
                             string='State', readonly=True, default='draft')
    part_ids = fields.Many2many('school.event.participant',
                                'event_participants_rel', 'participant_id',
                                'event_id', 'Participants', readonly=True,
                                order_by='score')
    code = fields.Many2one('school.school', 'Organizer School',
                           help='Event Organized School')
    is_holiday = fields.Boolean('Is Holiday(s)',
                                help='Checked if the event is organized\
                                      on holiday.')
    color = fields.Integer('Color Index', default=0)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        '''Raises constraint when start date is greater than end date'''
        sedt = self.start_date > self.end_date
        if (self.start_date and self.end_date and sedt):
            raise UserError(_('Error! Event start-date must be lower\
                              then Event end-date!'))

    @api.constrains('start_date', 'end_date', 'start_reg_date',
                    'last_reg_date')
    def _check_all_dates(self):

        dt = self.start_reg_date and self.last_reg_date
        if (self.start_date and self.end_date and dt):

            if self.start_reg_date > self.last_reg_date:
                raise UserError(_('Error! Event Registration StartDate must be\
                                  lower than Event Registration end-date.!'))
            elif self.last_reg_date >= self.start_date:
                raise UserError(_('Error! Event Registration last-date must be\
                                    lower than Event start-date!.'))

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False,
                access_rights_uid=None):
        '''Override method to find student of standard selected'''
        if self._context.get('part_name_id'):
            student_obj = self.env['student.student']
            data = student_obj.browse(self._context.get('part_name_id'))
            arg_domain = ('part_standard_ids', 'in', [data.standard_id.id])
            args.append(arg_domain)
        return super(SchoolEvent, self
                     )._search(args=args, offset=offset,
                               limit=limit, count=count,
                               access_rights_uid=access_rights_uid)

    @api.multi
    def event_open(self):
        for rec in self:
            if len(rec.part_ids) >= 1:
                rec.state = 'open'
            else:
                raise UserError(_('No Participants ! \
                             No Participants to open the Event!'))

    @api.multi
    def event_close(self):
        '''Method to change state to close'''
        self.write({'state': 'close'})
        return True

    @api.multi
    def event_draft(self):
        '''Method to change state to draft'''
        self.write({'state': 'draft'})
        return True

    @api.multi
    def event_cancel(self):
        '''Method to change state to cancel'''
        self.write({'state': 'cancel'})
        return True


class SchoolEventRegistration(models.Model):
    '''for registration by students for events'''
    _name = 'school.event.registration'
    _description = 'Event Registration'
    _rec_name = "reg_date"

    name = fields.Many2one('school.event', 'Event Name',
                           domain=[('state', '=', 'draft')], required=True,
                           help="Name of event")
    part_name_id = fields.Many2one('student.student', 'Participant Name',
                                   required=True,
                                   help="Select Participant")
    reg_date = fields.Date('Registration Date', readonly=True,
                           help="Registration date of event",
                           default=lambda *a:
                           time.strftime("%Y-%m-%d %H:%M:%S"))
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirm'),
                              ('cancel', 'Cancel')], 'State', readonly=True,
                             default='draft')
    is_holiday = fields.Boolean('Is Holiday(s)', help='Checked if the event is\
                                                    organized on holiday.')

    @api.multi
    def regi_cancel(self):
        '''Method to cancel registration'''
        event_part_obj = self.env['school.event.participant']
        for rec in self:
            prt_data = rec.part_name_id
            # delete entry of participant
            domain = [('stu_pid', '=', rec.part_name_id.pid),
                      ('event_id', '=', rec.name.id),
                      ('name', '=', prt_data.id)]
            stu_prt_data = event_part_obj.search(domain)
            stu_prt_data.sudo().unlink()
            rec.write({'state': 'cancel'})
        return True

    @api.multi
    def regi_confirm(self):
        '''Method to confirm registration'''
        event_part_obj = self.env['school.event.participant']

        for rec in self:
            participants = int(rec.name.participants) + 1

            # check participation is full or not.
            if participants > rec.name.maximum_participants:
                raise UserError(_('Error ! \
                                 Participation in this Event is Full.'))

            # check last registration date is over or not
            if rec.reg_date > rec.name.last_reg_date:
                raise UserError(_('Error ! Last Registration date is over \
                                   for this Event.'))
            # make entry in participant
            vals = {'stu_pid': str(rec.part_name_id.pid),
                    'win_parameter_id': rec.name.parameter_id.id,
                    'event_id': rec.name.id,
                    'name': rec.part_name_id.id}
            part_id = event_part_obj.sudo().create(vals)
            rec.name.sudo().write({'part_ids': [(4, part_id.ids)]})
            rec.part_name_id.sudo().write({'event_ids': [(4, part_id.ids)]})
            rec.write({'state': 'confirm'})
        return True


class StudentStudent(models.Model):
    _name = 'student.student'
    _inherit = 'student.student'
    _description = 'Student Information'

    event_ids = fields.Many2many('school.event.participant',
                                 'student_participants_rel', 'stud_id',
                                 'participant_id', 'Participants')

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False,
                access_rights_uid=None):
        '''Override method to find event of standard selected'''
        if self._context.get('name'):
            event_obj = self.env['school.event']
            event_data = event_obj.browse(self._context['name'])
            std_ids = [std_id.id for std_id in event_data.part_standard_ids]
            args.append(('standard_id', 'in', std_ids))
        return super(StudentStudent, self)._search(
            args=args, offset=offset, limit=limit, order=order, count=count,
            access_rights_uid=access_rights_uid)
