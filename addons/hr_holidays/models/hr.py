# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
    absent_employee_ids = fields.One2many(
        'hr.employee', string='Absent Employees', compute='_compute_absent_employee_ids')

    @api.multi
    def _compute_absent_employee_ids(self):
        # seems odd to take midnight in utc instead of midnight in user's tz ... but that's how it's done below
        today_date = datetime.datetime.utcnow().date()
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        for department in self:
            data = self.env['hr.holidays'].search_read(
                [('department_id', '=', department.id), ('state', '!=', 'refuse'),
                 ('date_from', '<=', today_end), ('date_to', '>=', today_start), ('type', '=', 'remove')],
                ['employee_id'])
            ids = [d['employee_id'][0] for d in data]
            department.absent_employee_ids = self.env['hr.employee'].browse(ids)

    @api.multi
    def _compute_leave_count(self):
        Holiday = self.env['hr.holidays']
        today_date = datetime.datetime.utcnow().date() # TIMEZONE ISSUES ! if I live in UTC+12 and want to see who's gone at 8 am it can be wrong.
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))

        # why 3 different read_groups ?
        leave_data = Holiday.read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm'), ('type', '=', 'remove')], # validate1 ?
            ['department_id'], ['department_id'])
        allocation_data = Holiday.read_group(
            [('department_id', 'in', self.ids),
             ('state', '=', 'confirm'), ('type', '=', 'add')], # validate1 ?
            ['department_id'], ['department_id'])
        absence_data = Holiday.read_group(
            [('department_id', 'in', self.ids), ('state', 'not in', ['draft', 'refuse']),
             ('date_from', '<=', today_end), ('date_to', '>=', today_start), ('type', '=', 'remove')],
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

    @api.model
    def retrieve_dashboard_data(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1).id
        leave_types_data = self.env['hr.holidays.status'].with_context(employee_id=employee_id).search_read(
            domain=[('active', '=', True)],
            fields=['id', 'name', 'virtual_remaining_leaves', 'leaves_taken', 'max_leaves', 'limit', 'next_expiration_date', 'next_expiration_amount'],
            order='virtual_remaining_leaves desc')
        # double the work but half the code !
        allocated_leaves = [d for d in leave_types_data if not d['limit'] and d['max_leaves'] > 0]
        limitless_leaves = [d for d in leave_types_data if d['limit']]
        # pending_leaves_count = self.env['hr.holidays'].search_count([('employee_id', '=', employee_id), ('state', 'in', ['confirm', 'validate1']), ('type', '=', 'remove')])
        # pending_allocations_count = self.env['hr.holidays'].search_count([('employee_id', '=', employee_id), ('state', 'in', ['confirm', 'validate1']), ('type', '=', 'add')])
        return {
            'employee_id': employee_id,
            # 'pending_leaves_count': pending_leaves_count,
            # 'pending_allocations_count': pending_allocations_count,
            'allocated_leaves': allocated_leaves,
            'limitless_leaves': limitless_leaves,
        }


class Employee(models.Model):

    _inherit = "hr.employee"

    remaining_leaves = fields.Float(compute='_compute_remaining_leaves', string='Remaining Legal Leaves', inverse='_inverse_remaining_leaves',
        help='Total number of legal leaves allocated to this employee, change this value to create allocation/leave request. '
             'Total based on all the leave types without overriding limit.')
    current_leave_state = fields.Selection(compute='_compute_leave_status', string="Current Leave Status",
        selection=[ # why all of the different status's when all you want to know is if it's validated or not. -> replace by boolean ?
            ('draft', 'New'),
            ('confirm', 'Waiting Approval'),
            ('refuse', 'Refused'), # why ? it'll never take this value
            ('validate1', 'Waiting Second Approval'),
            ('validate', 'Approved'),
        ])
    current_leave_id = fields.Many2one('hr.holidays.status', compute='_compute_leave_status', string="Current Leave Type")
    leave_date_from = fields.Date('From Date', compute='_compute_leave_status')
    leave_date_to = fields.Date('To Date', compute='_compute_leave_status')
    leaves_count = fields.Float('Number of Leaves', compute='_compute_leaves_count') # same field as remaining leaves, only doesn't bypass access rights...
    show_leaves = fields.Boolean('Able to see Remaining Leaves', compute='_compute_show_leaves')
    is_absent_totay = fields.Boolean('Absent Today', compute='_compute_absent_employee', search='_search_absent_employee')

    def _get_remaining_leaves(self):
        """ Helper to compute the remaining leaves for the current employees
            :returns dict where the key is the employee id, and the value is the remain leaves
        """
        # why is this written in sql ? guess access rules aren't an issue but did this have perf issues ?
        # change comparing to before: takes leaves to approve into account, but it's now in sync with the rest of the module's logic.
        self._cr.execute("""
            SELECT
                sum(h.number_of_days - coalesce(hres.days_reserved, 0)) AS days,
                h.employee_id
            FROM
                hr_holidays h
                left join hr_holidays_reservation hres ON (hres.allocation_id=h.id)
            WHERE
                h.state='validate' AND
                h.type='add' AND
                h.employee_id in %s
            GROUP BY h.employee_id""", (tuple(self.ids),))
        return dict((row['employee_id'], row['days']) for row in self._cr.dictfetchall())

    @api.multi
    def _compute_remaining_leaves(self):
        remaining = self._get_remaining_leaves()
        for employee in self:
            employee.remaining_leaves = remaining.get(employee.id, 0.0)

    @api.multi
    def _inverse_remaining_leaves(self): # THIS FEATURE IS BROKEN, the field doesn't display legal leaves only and it won't necessarily create one of that type... -> correct or drop feature ? (seems way too volatile to me)
        status_list = self.env['hr.holidays.status'].search([('limit', '=', False)])
        # Create leaves (adding remaining leaves) or raise (reducing remaining leaves)
        actual_remaining = self._get_remaining_leaves()
        for employee in self.filtered(lambda employee: employee.remaining_leaves):
            # check the status list. This is done here and not before the loop to avoid raising
            # exception on employee creation (since we are in a computed field).
            if len(status_list) != 1:
                raise UserError(_("The feature behind the field 'Remaining Legal Leaves' can only be used when there is only one "
                    "leave type with the option 'Allow to Override Limit' unchecked. (%s Found). "
                    "Otherwise, the update is ambiguous as we cannot decide on which leave type the update has to be done. "
                    "\n You may prefer to use the classic menus 'Leave Requests' and 'Allocation Requests' located in Leaves Application "
                    "to manage the leave days of the employees if the configuration does not allow to use this field.") % (len(status_list)))
            status = status_list[0] if status_list else None
            if not status:
                continue
            # if a status is found, then compute remaing leave for current employee
            difference = employee.remaining_leaves - actual_remaining.get(employee.id, 0)
            if difference > 0:
                leave = self.env['hr.holidays'].create({
                    'name': _('Allocation for %s') % employee.name,
                    'employee_id': employee.id,
                    'holiday_status_id': status.id,
                    'type': 'add',
                    'holiday_type': 'employee',
                    'number_of_days_temp': difference
                })
                leave.action_approve()
                if leave.double_validation:
                    leave.action_validate()
            elif difference < 0:
                raise UserError(_('You cannot reduce validated allocation requests'))

    @api.multi
    def _compute_leave_status(self):
        # Used SUPERUSER_ID to forcefully get status of other user's leave, to bypass record rule
        holidays = self.env['hr.holidays'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('date_from', '<=', fields.Datetime.now()), # why is this compared to now(), but the absent employee id above relative to the day ?
            ('date_to', '>=', fields.Datetime.now()),
            ('type', '=', 'remove'),
            ('state', 'not in', ('draft', 'refuse')),
        ])
        leave_data = {}
        for holiday in holidays:
            leave_data[holiday.employee_id.id] = {}
            leave_data[holiday.employee_id.id]['leave_date_from'] = holiday.date_from
            leave_data[holiday.employee_id.id]['leave_date_to'] = holiday.date_to
            leave_data[holiday.employee_id.id]['current_leave_state'] = holiday.state
            leave_data[holiday.employee_id.id]['current_leave_id'] = holiday.holiday_status_id.id

        for employee in self:
            employee.leave_date_from = leave_data.get(employee.id, {}).get('leave_date_from')
            employee.leave_date_to = leave_data.get(employee.id, {}).get('leave_date_to')
            employee.current_leave_state = leave_data.get(employee.id, {}).get('current_leave_state')
            employee.current_leave_id = leave_data.get(employee.id, {}).get('current_leave_id')

    @api.multi
    def _compute_leaves_count(self):
        leaves = self.env['hr.holidays'].read_group([
            ('employee_id', 'in', self.ids),
            ('holiday_status_id.limit', '=', False),
            ('state', '=', 'validate')
        ], fields=['number_of_days', 'employee_id'], groupby=['employee_id'])
        mapping = dict([(leave['employee_id'][0], leave['number_of_days']) for leave in leaves])
        for employee in self:
            employee.leaves_count = mapping.get(employee.id)

    @api.multi
    def _compute_show_leaves(self): # why is this a field ... who wrote this crappy compute anyway
        show_leaves = self.env['res.users'].has_group('hr_holidays.group_hr_holidays_user')
        for employee in self:
            if show_leaves or employee.user_id == self.env.user:
                employee.show_leaves = True
            else:
                employee.show_leaves = False

    @api.multi
    def _compute_absent_employee(self): # so much duplicate code, why doesn't the department stuff use this ?
        today_date = datetime.datetime.utcnow().date() # TIMEZONE ISSUES
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        data = self.env['hr.holidays'].read_group([
            ('employee_id', 'in', self.ids),
            ('state', 'not in', ['draft', 'refuse']),
            ('date_from', '<=', today_end), # here we are working with day start & end again ...
            ('date_to', '>=', today_start),
            ('type', '=', 'remove')
        ], ['employee_id'], ['employee_id'])
        result = dict.fromkeys(self.ids, False)
        for item in data:
            if item['employee_id_count'] >= 1:
                result[item['employee_id'][0]] = True
        for employee in self:
            employee.is_absent_totay = result[employee.id]

    @api.multi
    def _search_absent_employee(self, operator, value):
        today_date = datetime.datetime.utcnow().date() # timezones again
        today_start = fields.Datetime.to_string(today_date)  # get the midnight of the current utc day
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        holidays = self.env['hr.holidays'].sudo().search([
            ('employee_id', '!=', False),
            ('state', 'not in', ['draft', 'refuse']),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start),
            ('type', '=', 'remove')
        ])
        return [('id', 'in', holidays.mapped('employee_id').ids)]
