# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import math
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.tools.float_utils import float_round


class Department(models.Model):

    _inherit = 'hr.department'

    absence_of_today = fields.Integer(
        compute='_compute_leave_count', string='Absence by Today')
    leave_to_approve_count = fields.Integer(
        compute='_compute_leave_count', string='Leave to Approve')
    allocation_to_approve_count = fields.Integer(
        compute='_compute_leave_count', string='Allocation to Approve')
    total_employee = fields.Integer(
        compute='_compute_total_employee', string='Total Employee')

    @api.multi
    def _compute_leave_count(self):
        Requests = self.env['hr.leave']
        Allocations = self.env['hr.leave.allocation']
        today_date = datetime.datetime.utcnow().date()
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))

        leave_data = Requests.read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm')],
            ['department_id'], ['department_id'])
        allocation_data = Allocations.read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm')],
            ['department_id'], ['department_id'])
        absence_data = Requests.read_group(
            [('department_id', 'in', self.ids), ('state', 'not in', ['cancel', 'refuse']),
             ('date_from', '<=', today_end), ('date_to', '>=', today_start)],
            ['department_id'], ['department_id'])

        res_leave = dict((data['department_id'][0], data['department_id_count']) for data in leave_data)
        res_allocation = dict((data['department_id'][0], data['department_id_count']) for data in allocation_data)
        res_absence = dict((data['department_id'][0], data['department_id_count']) for data in absence_data)

        for department in self:
            department.leave_to_approve_count = res_leave.get(department.id, 0)
            department.allocation_to_approve_count = res_allocation.get(department.id, 0)
            department.absence_of_today = res_absence.get(department.id, 0)

    @api.multi
    def _compute_total_employee(self):
        emp_data = self.env['hr.employee'].read_group([('department_id', 'in', self.ids)], ['department_id'], ['department_id'])
        result = dict((data['department_id'][0], data['department_id_count']) for data in emp_data)
        for department in self:
            department.total_employee = result.get(department.id, 0)


class Employee(models.Model):
    _inherit = "hr.employee"

    remaining_leaves = fields.Float(
        compute='_compute_remaining_leaves', string='Remaining Legal Leaves',
        help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave request. '
             'Total based on all the leave types without overriding limit.')
    current_leave_state = fields.Selection(compute='_compute_leave_status', string="Current Leave Status",
        selection=[
            ('draft', 'New'),
            ('confirm', 'Waiting Approval'),
            ('refuse', 'Refused'),
            ('validate1', 'Waiting Second Approval'),
            ('validate', 'Approved'),
            ('cancel', 'Cancelled')
        ])
    current_leave_id = fields.Many2one('hr.leave.type', compute='_compute_leave_status', string="Current Leave Type")
    leave_date_from = fields.Date('From Date', compute='_compute_leave_status')
    leave_date_to = fields.Date('To Date', compute='_compute_leave_status')
    leaves_count = fields.Float('Number of Leaves', compute='_compute_leaves_count')
    show_leaves = fields.Boolean('Able to see Remaining Leaves', compute='_compute_show_leaves')
    is_absent_totay = fields.Boolean('Absent Today', compute='_compute_absent_employee', search='_search_absent_employee')

    def _get_remaining_leaves(self):
        """ Helper to compute the remaining leaves for the current employees
            :returns dict where the key is the employee id, and the value is the remain leaves
        """
        self._cr.execute("""
            SELECT
                sum(h.number_of_days) AS days,
                h.employee_id
            FROM
                (
                    SELECT holiday_status_id, number_of_days,
                        state, employee_id
                    FROM hr_leave_allocation
                    UNION
                    SELECT holiday_status_id, (number_of_days * -1) as number_of_days,
                        state, employee_id
                    FROM hr_leave
                ) h
                join hr_leave_type s ON (s.id=h.holiday_status_id)
            WHERE
                h.state='validate' AND
                (s.allocation_type='fixed' OR s.allocation_type='fixed_allocation') AND
                h.employee_id in %s
            GROUP BY h.employee_id""", (tuple(self.ids),))
        return dict((row['employee_id'], row['days']) for row in self._cr.dictfetchall())

    @api.multi
    def _compute_remaining_leaves(self):
        remaining = self._get_remaining_leaves()
        for employee in self:
            remaining_days = remaining.get(employee.id, 0.0)
            if remaining_days is None:
                remaining_days = 0.0
            employee.remaining_leaves = float_round(remaining_days, precision_digits=2)

    @api.multi
    def _compute_leave_status(self):
        # Used SUPERUSER_ID to forcefully get status of other user's leave, to bypass record rule
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('date_from', '<=', fields.Datetime.now()),
            ('date_to', '>=', fields.Datetime.now()),
            ('state', 'not in', ('cancel', 'refuse'))
        ])
        leave_data = {}
        for holiday in holidays:
            leave_data[holiday.employee_id.id] = {}
            leave_data[holiday.employee_id.id]['leave_date_from'] = holiday.date_from.date()
            leave_data[holiday.employee_id.id]['leave_date_to'] = holiday.date_to.date()
            leave_data[holiday.employee_id.id]['current_leave_state'] = holiday.state
            leave_data[holiday.employee_id.id]['current_leave_id'] = holiday.holiday_status_id.id

        for employee in self:
            employee.leave_date_from = leave_data.get(employee.id, {}).get('leave_date_from')
            employee.leave_date_to = leave_data.get(employee.id, {}).get('leave_date_to')
            employee.current_leave_state = leave_data.get(employee.id, {}).get('current_leave_state')
            employee.current_leave_id = leave_data.get(employee.id, {}).get('current_leave_id')

    @api.multi
    def _compute_leaves_count(self):
        all_leaves = self.env['hr.leave.report'].read_group([
            ('employee_id', 'in', self.ids),
            ('state', '=', 'validate')
        ], fields=['number_of_days', 'employee_id'], groupby=['employee_id'])
        mapping = dict([(leave['employee_id'][0], leave['number_of_days']) for leave in all_leaves])
        for employee in self:
            employee.leaves_count = float_round(mapping.get(employee.id, 0), precision_digits=2)

    @api.multi
    def _compute_show_leaves(self):
        show_leaves = self.env['res.users'].has_group('hr_holidays.group_hr_holidays_user')
        for employee in self:
            if show_leaves or employee.user_id == self.env.user:
                employee.show_leaves = True
            else:
                employee.show_leaves = False

    @api.multi
    def _compute_absent_employee(self):
        today_date = datetime.datetime.utcnow().date()
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        data = self.env['hr.leave'].read_group([
            ('employee_id', 'in', self.ids),
            ('state', 'not in', ['cancel', 'refuse']),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start)
        ], ['employee_id'], ['employee_id'])
        result = dict.fromkeys(self.ids, False)
        for item in data:
            if item['employee_id_count'] >= 1:
                result[item['employee_id'][0]] = True
        for employee in self:
            employee.is_absent_totay = result[employee.id]

    @api.multi
    def _search_absent_employee(self, operator, value):
        today_date = datetime.datetime.utcnow().date()
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', '!=', False),
            ('state', 'not in', ['cancel', 'refuse']),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start)
        ])
        return [('id', 'in', holidays.mapped('employee_id').ids)]

    # function to add all mandatory leaves in the future
    def add_mandatory_leaves(self, resource_calendar_id, employee_id):
        today_date_str = fields.Datetime.to_string(datetime.datetime.utcnow().date())
        leaves = self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', resource_calendar_id),
            ('resource_id', '=', False),
            ('generate_hr_leaves', '=', True),
            ('date_to', '>=', today_date_str)
        ])

        problem_name = []

        for leave in leaves:
            date_from = leave.date_from
            date_to = leave.date_to
            if isinstance(date_from, str):
                date_from = fields.Datetime.from_string(date_from)
            if isinstance(date_to, str):
                date_to = fields.Datetime.from_string(date_to)
            time_delta = date_to - date_from
            number_of_days = math.ceil(time_delta.days + float(time_delta.seconds) / 86400)
            try:
                request = self.env['hr.leave'].with_context(auto_leave_create_disable=True).create({
                    'name': leave.name,
                    'employee_id': employee_id,
                    'holiday_status_id': leave.company_id.bank_leaves_type_id.id,
                    'request_date_from': leave.date_from,
                    'request_date_to': leave.date_to,
                    'date_from': leave.date_from,
                    'date_to': leave.date_to,
                    'number_of_days': number_of_days,
                    'calendar_leave_id': leave.id,
                })
                request.action_approve()
            except:
                problem_name.append('%(name)s (%(from)s - %(to)s)' %{'name': leave.name, 'from': leave.date_from, 'to': leave.date_to})
                continue

        if len(problem_name):
            raise Warning(_('Conflict with leave(s):\n %(employee)s') % {'employee': '\n'.join(problem_name)})


    # function to remove all mandatory leaves in the past
    def remove_mandatory_leaves(self, resource_calendar_id, employee_id):
        today_date_str = fields.Datetime.to_string(datetime.datetime.utcnow().date())
        leaves = self.env['resource.calendar.leaves'].search([
            ('calendar_id', '=', resource_calendar_id),
            ('resource_id', '=', False),
            ('generate_hr_leaves', '=', True),
            ('date_from', '>=', today_date_str)
        ])

        for leave in leaves:
            request_to_delete = self.env['hr.leave'].search([
                ('calendar_leave_id', '=', leave.id),
                ('employee_id', '=', employee_id)
            ])
            request_to_delete.action_refuse()
            request_to_delete.action_draft()
            request_to_delete.unlink()

    @api.model
    def create(self, values):
        res = super(Employee, self).create(values)
        self.add_mandatory_leaves(values.get('resource_calendar_id', 1), res.id)
        return res

    def write(self, values):
        old_resource_calendar_id = self.resource_calendar_id.id
        res = super(Employee, self).write(values)
        today_date = fields.Datetime.now()
        if 'parent_id' in values or 'department_id' in values:
            hr_vals = {}
            if values.get('parent_id') is not None:
                hr_vals['manager_id'] = values['parent_id']
            if values.get('department_id') is not None:
                hr_vals['department_id'] = values['department_id']
            holidays = self.env['hr.leave'].search(['|', ('state', 'in', ['draft', 'confirm']), ('date_from', '>', today_date), ('employee_id', 'in', self.ids)])
            holidays.write(hr_vals)
            allocations = self.env['hr.leave.allocation'].search([('state', 'in', ['draft', 'confirm']), ('employee_id', 'in', self.ids)])
            allocations.write(hr_vals)
        if 'resource_calendar_id' in values:
            self.remove_mandatory_leaves(old_resource_calendar_id, self.id)
            self.add_mandatory_leaves(values.get('resource_calendar_id', 1), self.id)
        return res
