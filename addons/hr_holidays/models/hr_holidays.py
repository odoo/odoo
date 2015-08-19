# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from datetime import timedelta

from openerp import api, fields, models, _
from openerp.exceptions import AccessError, UserError


class HrHolidays(models.Model):
    _name = "hr.holidays"
    _description = "Leave"
    _order = "request_type desc, date_from asc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _default_employee_get(self):
        if self.env.context.get('default_employee_id'):
            return self.env.context['default_employee_id']
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        return employee.id or False

    name = fields.Char(string='Description')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
    ], string='Status', readonly=True, track_visibility='onchange', copy=False,
        help='The status is set to \'To Submit\', when a holiday request is created.\n'
             'The status is \'To Approve\', when holiday request is confirmed by user.\n'
             'The status is \'Refused\', when holiday request is refused by manager.\n'
             'The status is \'Approved\', when holiday request is approved by manager.',
        default='confirm')
    payslip_status = fields.Boolean(string='Reported in last payslips',
        help='Green this button when the leave has been taken into account '
             'in the payslip.', default=False)
    report_note = fields.Text(string='HR Comments')
    user_id = fields.Many2one('res.users', related='employee_id.user_id',
        string='User', default=lambda self: self.env.user.id)
    date_from = fields.Datetime(string='Start Date', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        index=True, copy=False)
    date_to = fields.Datetime(string='End Date', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        copy=False)
    holiday_status_id = fields.Many2one('hr.holidays.status',
        string='Leave Type', required=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True,
        invisible=False, readonly=True, default=lambda self: self._default_employee_get(),
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    manager_id = fields.Many2one('hr.employee', string='First Approval',
        invisible=False, readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the leave')
    notes = fields.Text(string='Reasons', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    number_of_days_temp = fields.Float(string='Allocation', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        copy=False)
    number_of_days = fields.Float(compute='_compute_number_of_days',
        string='Number of Days', store=True)
    meeting_id = fields.Many2one('calendar.event', string='Meeting')
    request_type = fields.Selection([
        ('remove', 'Leave Request'),
        ('add', 'Allocation Request')
    ], string='Request Type', required=True, readonly=True, index=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='Choose \'Leave Request\' if someone wants to take an off-day. \n'
             'Choose \'Allocation Request\' if you want to increase the number '
             'of leaves available for someone', default='remove')
    parent_id = fields.Many2one('hr.holidays', string='Parent')
    linked_request_ids = fields.One2many('hr.holidays', 'parent_id',
        string='Linked Requests')
    department_id = fields.Many2one('hr.department',
        related='employee_id.department_id', string='Department', readonly=True, store=True)
    category_id = fields.Many2one('hr.employee.category', string='Employee Tag',
        help='Category of Employee', readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('category', 'By Employee Tag')], string='Allocation Mode',
        readonly=True, required=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help='By Employee: Allocation/Request for individual Employee,'
             'By Employee Tag: Allocation/Request for group of employees in category',
        default='employee')
    second_manager_id = fields.Many2one('hr.employee', string='Second Approval',
        readonly=True, copy=False, oldname='manager_id2',
        help='This area is automaticly filled by the user who validate the '
             'leave with second level (If Leave type need second validation)')
    double_validation = fields.Boolean(comodel_name='hr.holidays.status',
        related='holiday_status_id.double_validation', string='Apply Double Validation')
    can_reset = fields.Boolean(compute='_compute_get_can_reset', string="Can reset")

    _sql_constraints = [
        ('type_value', "CHECK ( \
                (holiday_type='employee' AND employee_id IS NOT NULL) or \
                (holiday_type='category' AND category_id IS NOT NULL) \
            )", _("The employee or employee category of this request is missing."
                  "Please make sure that your user login is linked to an employee.")),
        ('date_check2', "CHECK ( \
                (request_type='add') OR (date_from <= date_to) \
            )", _("The start date must be anterior to the end date.")),
        ('date_check', "CHECK ( number_of_days_temp >= 0 )",
            _("The number of days must be greater than 0.")),
    ]

    @api.depends('request_type')
    def _compute_number_of_days(self):
        for record in self:
            if record.request_type == 'remove':
                record.number_of_days = -record.number_of_days_temp
            else:
                record.number_of_days = record.number_of_days_temp

    def _compute_get_can_reset(self):
        """User can reset a leave request if it is its own leave request or if
        he is an Hr Manager. """
        hr_manager_group = self.env.ref('base.group_hr_manager')
        user_groups = [g for g in self.env.user.groups_id]
        for record in self:
            if hr_manager_group in user_groups:
                record.can_reset = True
            if record.employee_id.user_id == self.env.user:
                record.can_reset = True

    @api.multi
    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            return 'hr_holidays.mt_holidays_approved'
        elif 'state' in init_values and self.state == 'validate1':
            return 'hr_holidays.mt_holidays_first_validated'
        elif 'state' in init_values and self.state == 'confirm':
            return 'hr_holidays.mt_holidays_confirmed'
        elif 'state' in init_values and self.state == 'refuse':
            return 'hr_holidays.mt_holidays_refused'
        return super(HrHolidays, self)._track_subtype(init_values)

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        domain = [
            ('date_from', '<=', self.date_to),
            ('date_to', '>=', self.date_from),
            ('employee_id', '=', self.employee_id.id),
            ('id', '!=', self.id),
            ('state', 'not in', ['cancel', 'refuse']),
        ]
        leaves_taken = self.search_count(domain)
        if leaves_taken:
            raise UserError(_('You can not have 2 leaves that overlaps on same day!'))

    @api.constrains('state', 'number_of_days_temp')
    def _check_holidays(self):
        ctx = dict(self.env.context, employee_id=self.employee_id.id)
        if self.holiday_type != 'employee' or self.request_type != 'remove' or \
           not self.employee_id or self.holiday_status_id.limit:
            return False

        leave_days = self.env['hr.holidays.status'].with_context(ctx).browse(
            self.holiday_status_id.id)
        if leave_days.remaining_leaves < 0 or \
           leave_days.virtual_remaining_leaves < 0:
            raise UserError(_('The number of remaining leaves is not sufficient for this leave '
                              'type.\n Please verify also the leaves waiting for validation.'))

    @api.onchange('holiday_type', 'employee_id')
    def _onchange_type(self):
        if self.holiday_type == 'employee' and not self.employee_id:
            employee = self.env['hr.employee'].search(
                [('user_id', '=', self.env.user.id)], limit=1)
            self.employee_id = employee.id
        elif self.holiday_type != 'employee':
            self.employee_id = False

    @api.onchange('employee_id')
    def _onchange_employee(self):
        self.department_id = self.employee_id.department_id.id

    @api.onchange('date_from', 'date_to')
    def _onchange_date_from(self):
        """If there are no date set for date_to, automatically set one 8 hours
        later than the date_from. Also update the number_of_days."""
        # date_to has to be greater than date_from
        if (self.date_from and self.date_to) and (self.date_from > self.date_to):
            raise UserError(_('The start date must be anterior to the end date.'))

        # Compute and update the number of days
        if (self.date_to and self.date_from) and (self.date_from <= self.date_to):
            diff_day = self._get_number_of_days(self.date_from, self.date_to)
            self.number_of_days_temp = round(math.floor(diff_day)) + 1
        else:
            self.number_of_days_temp = 0

        # No date_to set so far: automatically compute one 8 hours later
        if self.date_from and not self.date_to:
            date_from = fields.Datetime.from_string(self.date_from)
            date_to_with_delta = date_from + timedelta(hours=8)
            self.date_to = fields.Datetime.to_string(date_to_with_delta)

    @api.onchange('date_from', 'date_to')
    def _onchange_date_to(self):
        """Update the number_of_days."""
        # date_to has to be greater than date_from
        if (self.date_from and self.date_to) and (self.date_from > self.date_to):
            raise UserError(_('The start date must be anterior to the end date.'))

        # Compute and update the number of days
        if (self.date_to and self.date_from) and (self.date_from <= self.date_to):
            diff_day = self._get_number_of_days(self.date_from, self.date_to)
            self.number_of_days_temp = round(math.floor(diff_day)) + 1
        else:
            self.number_of_days_temp = 0

    @api.one
    def toggle_payslip_status(self):
        if self.payslip_status:
            return self.write({'payslip_status': False})
        else:
            return self.write({'payslip_status': True})

    @api.model
    def create(self, vals):
        """Override to avoid automatic logging of creation"""
        ctx = dict(self.env.context, mail_create_nolog=True)
        if vals.get('state') and \
           vals['state'] not in ['draft', 'confirm', 'cancel'] and \
           not self.env['res.users'].has_group('base.group_hr_user'):
            raise AccessError(_('You cannot set a leave request as \'%s\'. '
                                'Contact a human resource manager.') % vals['state'])
        holiday = super(HrHolidays, self.with_context(ctx)).create(vals)
        if vals.get('employee_id'):
            holiday.with_context(ctx).add_follower()
        return holiday

    @api.multi
    def write(self, vals):
        if vals.get('state') and \
           vals['state'] not in ['draft', 'confirm', 'cancel'] and \
           not self.env['res.users'].has_group('base.group_hr_user'):
            raise AccessError(_('You cannot set a leave request as \'%s\'. '
                                'Contact a human resource manager.') % vals.get('state'))
        res = super(HrHolidays, self).write(vals)
        if vals.get('employee_id'):
            self.add_follower()
        return res

    @api.multi
    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'cancel', 'confirm']:
                raise UserError(_('You cannot delete a leave which is '
                                  'in %s state.') % (record.state))
        return super(HrHolidays, self).unlink()

    def _get_number_of_days(self, date_from, date_to):
        """Returns a float equals to the timedelta between two dates
        given as string."""
        from_dt = fields.Datetime.from_string(date_from)
        to_dt = fields.Datetime.from_string(date_to)
        diff = to_dt - from_dt
        diff_day = diff.days + float(diff.seconds) / 86400
        return diff_day

    def add_follower(self):
        if self.employee_id.user_id:
            self.message_subscribe_users(user_ids=[self.employee_id.user_id.id])

    def _create_resource_leave(self):
        """This method will create entry in resource calendar leave object
        at the time of holidays validated """
        vals = {
            'name': self.name,
            'date_from': self.date_from,
            'holiday_id': self.id,
            'date_to': self.date_to,
            'resource_id': self.employee_id.resource_id.id,
            'calendar_id': self.employee_id.resource_id.calendar_id.id
        }
        self.env['resource.calendar.leaves'].create(vals)

    def _remove_resource_leave(self):
        """This method will create entry in resource calendar leave object
        at the time of holidays cancel/removed"""
        ResourceCalendarLeaves = self.env['resource.calendar.leaves'].search(
            [('holiday_id', 'in', self.ids)])
        ResourceCalendarLeaves.unlink()

    def holidays_reset(self):
        self.write({
            'state': 'draft',
            'manager_id': False,
            'second_manager_id': False,
        })
        to_unlink = self.env['hr.holidays']
        for rec in self:
            for record in rec.linked_request_ids:
                record.holidays_reset()
                to_unlink += record
        if to_unlink:
            to_unlink.unlink()
        return True

    def holidays_first_validate(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        self.write({
            'state': 'validate1',
            'manager_id': employee.id
        })

    def holidays_validate(self):
        HrEmployee = self.env['hr.employee']
        CalendarEvent = self.env['calendar.event']
        employee = HrEmployee.search([('user_id', '=', self.env.user.id)], limit=1)
        self.state = 'validate'

        for record in self:
            if record.double_validation:
                record.second_manager_id = employee.id
            else:
                record.manager_id = employee.id

            if record.holiday_type == 'employee' and record.request_type == 'remove':
                meeting_vals = {
                    'name': record.name or _('Leave Request'),
                    'categ_ids': (record.holiday_status_id.categ_id and
                                  [(6, 0, [record.holiday_status_id.categ_id.id])] or []),
                    'duration': record.number_of_days_temp * 8,
                    'description': record.notes,
                    'user_id': record.user_id.id,
                    'start': record.date_from,
                    'stop': record.date_to,
                    'allday': False,
                    'state': 'open',   # to block that meeting date in the calendar
                    'class': 'confidential'
                }
                #Add the partner_id (if exist) as an attendee
                if record.user_id and record.user_id.partner_id:
                    meeting_vals['partner_ids'] = [(4, record.user_id.partner_id.id)]

                meeting_id = CalendarEvent.with_context(no_email=True).create(meeting_vals)
                record._create_resource_leave()
                record.write({'meeting_id': meeting_id.id})
            elif record.holiday_type == 'category':
                employees = HrEmployee.search([
                    ('category_ids', 'child_of', [record.category_id.id])
                ])
                leaves = []
                for employee in employees:
                    vals = {
                        'name': record.name,
                        'request_type': record.request_type,
                        'holiday_type': 'employee',
                        'holiday_status_id': record.holiday_status_id.id,
                        'date_from': record.date_from,
                        'date_to': record.date_to,
                        'notes': record.notes,
                        'number_of_days_temp': record.number_of_days_temp,
                        'parent_id': record.id,
                        'employee_id': employee.id
                    }
                    leaves.append(record.create(vals))
                for leave in leaves:
                    # TODO is it necessary to interleave the calls?
                    for sig in ('confirm', 'validate', 'second_validate'):
                        leave.signal_workflow(sig)

    def holidays_confirm(self):
        for record in self.filtered(lambda record: record.employee_id.parent_id.user_id):
            record.message_subscribe_users([record.employee_id.parent_id.user_id.id])
        return self.write({'state': 'confirm'})

    def holidays_refuse(self):
        HrEmployee = self.env['hr.employee']
        employee = HrEmployee.search([('user_id', '=', self.env.user.id)], limit=1)
        for record in self:
            if self.state == 'validate1':
                self.write({'state': 'refuse', 'manager_id': employee.id})
            else:
                self.write({'state': 'refuse', 'second_manager_id': employee.id})
        self.holidays_cancel()

    def holidays_cancel(self):
        for record in self:
            # Delete the meeting
            if record.meeting_id:
                record.meeting_id.unlink()

            # If a category that created several holidays, cancel all related
            record.signal_workflow('refuse')
        self._remove_resource_leave()
