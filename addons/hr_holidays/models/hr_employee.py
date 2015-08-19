# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar

from dateutil.relativedelta import relativedelta

from openerp import api, fields, models, _
from openerp.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    remaining_leaves = fields.Float(string='Remaining Legal Leaves',
        compute='_compute_get_remaining_days', inverse='_inverse_set_remaining_days',
        help='Total number of legal leaves allocated to this employee, change '
             'this value to create allocation/leave request. Total based on '
             'all the leave types without overriding limit.')
    current_leave_state = fields.Selection([
        ('draft', 'New'),
        ('confirm', 'Waiting Approval'),
        ('refuse', 'Refused'),
        ('validate1', 'Waiting Second Approval'),
        ('validate', 'Approved'),
        ('cancel', 'Cancelled')
    ], compute='_compute_get_leave_status', string="Current Leave Status")
    current_leave_id = fields.Many2one(compute='_compute_get_leave_status',
        comodel_name='hr.holidays.status', string="Current Leave Type")
    leave_date_from = fields.Date(compute='_compute_get_leave_status', string='From Date')
    leave_date_to = fields.Date(compute='_compute_get_leave_status', string='To Date')
    leaves_count = fields.Integer(compute='_compute_leaves_count',
        string='Number of Leaves (current month)')
    approved_leaves_count = fields.Integer(compute='_compute_leaves_count',
        string='Approved Leaves not in Payslip',
        help='These leaves are approved but not taken into account for payslip')
    is_absent_today = fields.Boolean(compute='_compute_absent_employee',
        search='_search_absent_employee', string="Absent Today", default=False)

    @api.one
    def _compute_get_remaining_days(self):
        self.remaining_leaves = self.remaining_days_count()

    @api.one
    def _inverse_set_remaining_days(self):
        if not self.remaining_leaves:
            return False
        Holidays = self.env['hr.holidays']
        HolidaysStatus = self.env['hr.holidays.status']
        status = HolidaysStatus.search([('limit', '=', False)])
        if len(status) != 1:
            raise UserError(_('The feature behind the field \'Remaining '
                'Legal Leaves\' can only be used when there is only one '
                'leave type with the option \'Allow to Override Limit\' '
                'unchecked. (%s Found). '
                'Otherwise, the update is ambiguous as we cannot decide '
                'on which leave type the update has to be done. \n'
                'You may prefer to use the classic menus '
                '\'Leave Requests\' and \'Allocation Requests\' located '
                'in \'Human Resources \ Leaves\' to manage the leave days '
                'of the employees if the configuration does not allow to '
                'use this field.') % (len(status)))
        status_id = status and status[0].id or False
        if not status_id:
            return False

        before_remaining_leaves = self.remaining_days_count()
        diff = self.remaining_leaves - before_remaining_leaves
        if diff > 0:
            leave = Holidays.create({
                'name': _('Allocation for %s') % self.name,
                'employee_id': self.id,
                'holiday_status_id': status_id,
                'request_type': 'add',
                'holiday_type': 'employee',
                'number_of_days_temp': diff})
        elif diff < 0:
            raise UserError(_('You cannot reduce validated allocation requests'))
        else:
            return False
        for sig in ('confirm', 'validate', 'second_validate'):
            leave.signal_workflow(sig)
        return True

    @api.multi
    def _compute_get_leave_status(self):
        HrHolidays = self.env['hr.holidays']
        today_date = fields.Datetime.from_string(fields.Date.today())
        today_relative = today_date + relativedelta(hours=23, minutes=59, seconds=59)
        today_end = fields.Datetime.to_string(today_relative)
        for record in self:
            holiday = HrHolidays.search([('employee_id', '=', record.id),
                ('date_from', '<=', fields.Datetime.now()),
                ('date_to', '>=', today_end),
                ('request_type', '=', 'remove'),
                ('state', 'not in', ('cancel', 'refuse'))])
            if holiday:
                record.leave_date_from = holiday.date_from
                record.leave_date_to = holiday.date_to
                record.current_leave_state = holiday.state
                record.current_leave_id = holiday.holiday_status_id.id

    @api.multi
    def _compute_leaves_count(self):
        HrHolidays = self.env['hr.holidays']
        date_begin = fields.Date.from_string(fields.Date.today()) + relativedelta(day=1)
        date_end = date_begin + relativedelta(
            day=calendar.monthrange(date_begin.year, date_begin.month)[1]
        )
        for record in self:
            record.leaves_count = HrHolidays.search_count([
                ('employee_id', '=', record.id),
                ('request_type', '=', 'remove')])
            record.approved_leaves_count = HrHolidays.search_count([
                ('employee_id', '=', record.id),
                ('request_type', '=', 'remove'),
                ('date_from', '>=', fields.Date.to_string(date_begin)),
                ('date_from', '<=', fields.Date.to_string(date_end)),
                ('state', '=', 'validate'),
                ('payslip_status', '=', False)])

    @api.multi
    def _compute_absent_employee(self):
        today_date = fields.Datetime.from_string(fields.Date.today())
        today_start = fields.Datetime.to_string(today_date)
        today_relative = today_date + relativedelta(hours=23, minutes=59, seconds=59)
        today_end = fields.Datetime.to_string(today_relative)
        for record in self:
            holiday = self.env['hr.holidays'].search([
                ('employee_id', '=', record.id),
                ('state', 'not in', ['cancel', 'refuse']),
                ('date_from', '<=', today_end),
                ('date_to', '>=', today_start),
                ('request_type', '=', 'remove')])
            self.is_absent_today = True if holiday else False

    @api.multi
    def _search_absent_employee(self, operator, value):
        today_date = fields.Datetime.from_string(fields.Date.today())
        today_start = fields.Datetime.to_string(today_date)
        today_relative = today_date + relativedelta(hours=23, minutes=59, seconds=59)
        today_end = fields.Datetime.to_string(today_relative)
        holidays = self.env['hr.holidays'].search([
            ('state', 'not in', ['cancel', 'refuse']),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start),
            ('request_type', '=', 'remove')])

        absent_employees = [holiday.employee_id.id for holiday in holidays if holiday['employee_id']]
        return [('id', 'in', absent_employees)]

    def remaining_days_count(self):
        leaves = self.env['hr.holidays'].read_group([('employee_id', '=', self.id),
            ('state', '=', 'validate'), ('holiday_status_id.limit', '=', False)],
            ['number_of_days', 'employee_id'], ['employee_id'])
        remaining_days = 0.0
        for leave in leaves:
            remaining_days += leave['number_of_days']
        return remaining_days
