# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
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

    max_leaves = fields.Float(compute='_compute_leaves', string='Maximum Allowed',
        help='This value is given by the sum of all leaves requests with a positive value.')
    leaves_taken = fields.Float(compute='_compute_leaves', string='Leaves Already Taken',
        help='This value is given by the sum of all leaves requests with a negative value.')
    remaining_leaves = fields.Float(compute='_compute_leaves', string='Remaining Leaves',
        help='Maximum Leaves Allowed - Leaves Already Taken')
    virtual_remaining_leaves = fields.Float(compute='_compute_leaves', string='Virtual Remaining Leaves',
        help='Maximum Leaves Allowed - Leaves Already Taken - Leaves Waiting Approval')

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

    leave_ids = fields.One2many('hr.leave', 'employee_id', readonly=True)
    allocation_ids = fields.One2many('hr.leave.allocation', 'employee_id', readonly=True)

    @api.multi
    def get_remaining_leave_data(self, leave_types):
        result = {id: defaultdict(lambda: {}) for id in self.ids}

        if not leave_types:
            return {}

        # note: add only validated allocation even for the virtual
        # count; otherwise pending then refused allocation allow
        # the employee to create more leaves than possible

        self._cr.execute("""
                SELECT
                    subsub.employee_id,
                    subsub.leave_type,
                    sum(subsub.virtual_remaining_leaves) as virtual_remaining_leaves,
                    sum(subsub.leaves_taken) as leaves_taken,
                    sum(subsub.remaining_leaves) as remaining_leaves,
                    sum(subsub.max_leaves) as max_leaves
                FROM (SELECT
                    sub.employee_id,
                    sub.leave_type,
                    sub.type,
                    CASE WHEN sub.type = 'request' THEN sum(sub.number_of_days_neg) ELSE sum(sub.number_of_days) END AS virtual_remaining_leaves,
                    CASE WHEN sub.state = 'validate' THEN CASE WHEN sub.type = 'request' THEN sum(sub.number_of_days) ELSE 0 END ELSE 0 END AS leaves_taken,
                    CASE WHEN sub.state = 'validate' THEN CASE WHEN sub.type = 'request' THEN sum(sub.number_of_days_neg) ELSE sum(sub.number_of_days) END ELSE 0 END AS remaining_leaves,
                    CASE WHEN sub.state = 'validate' THEN CASE WHEN sub.type = 'request' THEN 0 ELSE sum(sub.number_of_days) END ELSE 0 END AS max_leaves
                    FROM (
                        SELECT
                            employee_id,
                            holiday_status_id as leave_type,
                            'request' as type,
                            state,
                            sum(number_of_days) as number_of_days,
                            -sum(number_of_days) as number_of_days_neg
                        FROM hr_leave
                        WHERE
                            holiday_status_id in %(leave_types)s
                            and state in ('confirm', 'validate1', 'validate')
                            and employee_id in %(employee_ids)s
                        GROUP BY employee_id, leave_type, state
                        UNION ALL
                        SELECT
                            employee_id,
                            holiday_status_id as leave_type,
                            'allocation' as type,
                            state,
                            sum(number_of_days) as number_of_days,
                            -sum(number_of_days) as number_of_days_neg
                        FROM hr_leave_allocation
                        WHERE
                            holiday_status_id in %(leave_types)s
                            and state = 'validate'
                            and employee_id in %(employee_ids)s
                        GROUP BY employee_id, leave_type, state
                        ) as sub
                    GROUP BY sub.type, sub.employee_id, sub.leave_type, sub.state) as subsub
            GROUP BY subsub.employee_id, subsub.leave_type
        """, {'leave_types': tuple(leave_types), 'employee_ids': tuple(self.ids)})

        for data in self._cr.dictfetchall():
            status_dict = result[data['employee_id']][data['leave_type']]
            status_dict['virtual_remaining_leaves'] = data['virtual_remaining_leaves']
            status_dict['leaves_taken'] = data['leaves_taken']
            status_dict['remaining_leaves'] = data['remaining_leaves']
            status_dict['max_leaves'] = data['max_leaves']

        return result

    @api.multi
    @api.depends('leave_ids', 'allocation_ids', 'leave_ids.state', 'leave_ids.holiday_status_id',
                 'allocation_ids.state', 'allocation_ids.holiday_status_id')
    def _compute_leaves(self):
        context_leave_types = self._context.get('holiday_status_ids', [])
        leave_types = self.env['hr.leave.type'].search([('allocation_type', 'in', ('fixed', 'fixed_allocation'))]).ids

        if not context_leave_types:
            return

        for employee in self:
            data_days = employee.get_remaining_leave_data(leave_types)

            for context_leave_type in context_leave_types:
                result = data_days[employee.id][context_leave_type]
                if result:
                    employee.max_leaves += result.get('max_leaves', 0)
                    employee.leaves_taken += result.get('leaves_taken', 0)
                    employee.remaining_leaves += result.get('remaining_leaves', 0)
                    employee.virtual_remaining_leaves += result.get('virtual_remaining_leaves', 0)

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

    def write(self, values):
        res = super(Employee, self).write(values)
        if 'parent_id' in values or 'department_id' in values:
            hr_vals = {}
            if values.get('parent_id') is not None:
                hr_vals['manager_id'] = values['parent_id']
            if values.get('department_id') is not None:
                hr_vals['department_id'] = values['department_id']
            holidays = self.env['hr.leave'].search([('state', 'in', ['draft', 'confirm']), ('employee_id', 'in', self.ids)])
            holidays.write(hr_vals)
            allocations = self.env['hr.leave.allocation'].search([('state', 'in', ['draft', 'confirm']), ('employee_id', 'in', self.ids)])
            allocations.write(hr_vals)
        return res
