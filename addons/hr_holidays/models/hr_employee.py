# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round
from odoo.addons.resource.models.resource import HOURS_PER_DAY
import pytz

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    leave_manager_id = fields.Many2one(
        'res.users', string='Time Off',
        compute='_compute_leave_manager', store=True, readonly=False,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        help='Select the user responsible for approving "Time Off" of this employee.\n'
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).')
    remaining_leaves = fields.Float(
        compute='_compute_remaining_leaves', string='Remaining Paid Time Off',
        help='Total number of paid time off allocated to this employee, change this value to create allocation/time off request. '
             'Total based on all the time off types without overriding limit.')
    current_leave_state = fields.Selection(compute='_compute_leave_status', string="Current Time Off Status",
        selection=[
            ('draft', 'New'),
            ('confirm', 'Waiting Approval'),
            ('refuse', 'Refused'),
            ('validate1', 'Waiting Second Approval'),
            ('validate', 'Approved'),
            ('cancel', 'Cancelled')
        ])
    leave_date_from = fields.Date('From Date', compute='_compute_leave_status')
    leave_date_to = fields.Date('To Date', compute='_compute_leave_status')
    leaves_count = fields.Float('Number of Time Off', compute='_compute_remaining_leaves')
    allocation_count = fields.Float('Total number of days allocated.', compute='_compute_allocation_count')
    allocations_count = fields.Integer('Total number of allocations', compute="_compute_allocation_count")
    show_leaves = fields.Boolean('Able to see Remaining Time Off', compute='_compute_show_leaves')
    is_absent = fields.Boolean('Absent Today', compute='_compute_leave_status', search='_search_absent_employee')
    allocation_display = fields.Char(compute='_compute_allocation_count')
    allocation_remaining_display = fields.Char(compute='_compute_allocation_remaining_display')
    hr_icon_display = fields.Selection(selection_add=[('presence_holiday_absent', 'On leave'),
                                                      ('presence_holiday_present', 'Present but on leave')])

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
                    UNION ALL
                    SELECT holiday_status_id, (number_of_days * -1) as number_of_days,
                        state, employee_id
                    FROM hr_leave
                ) h
                join hr_leave_type s ON (s.id=h.holiday_status_id)
            WHERE
                s.active = true AND h.state='validate' AND
                s.requires_allocation='yes' AND
                h.employee_id in %s
            GROUP BY h.employee_id""", (tuple(self.ids),))
        return dict((row['employee_id'], row['days']) for row in self._cr.dictfetchall())

    def _compute_remaining_leaves(self):
        remaining = {}
        if self.ids:
            remaining = self._get_remaining_leaves()
        for employee in self:
            value = float_round(remaining.get(employee.id, 0.0), precision_digits=2)
            employee.leaves_count = value
            employee.remaining_leaves = value

    def _compute_allocation_count(self):
        # Don't get allocations that are expired
        current_date = datetime.date.today()
        data = self.env['hr.leave.allocation']._read_group([
            ('employee_id', 'in', self.ids),
            ('holiday_status_id.active', '=', True),
            ('holiday_status_id.requires_allocation', '=', 'yes'),
            ('state', '=', 'validate'),
            ('date_from', '<=', current_date),
            ('date_to', '>=', current_date),
        ], ['number_of_days:sum', 'employee_id'], ['employee_id'])
        rg_results = dict((d['employee_id'][0], {"employee_id_count": d['employee_id_count'], "number_of_days": d['number_of_days']}) for d in data)
        for employee in self:
            result = rg_results.get(employee.id)
            employee.allocation_count = float_round(result['number_of_days'], precision_digits=2) if result else 0.0
            employee.allocation_display = "%g" % employee.allocation_count
            employee.allocations_count = result['employee_id_count'] if result else 0.0

    def _compute_allocation_remaining_display(self):
        allocations = self.env['hr.leave.allocation'].search([('employee_id', 'in', self.ids)])
        leaves_taken = allocations.holiday_status_id._get_employees_days_per_allocation(self.ids)
        for employee in self:
            employee_remaining_leaves = 0
            for leave_type in leaves_taken[employee.id]:
                if leave_type.requires_allocation == 'no':
                    continue
                for allocation in leaves_taken[employee.id][leave_type]:
                    if allocation:
                        virtual_remaining_leaves = leaves_taken[employee.id][leave_type][allocation]['virtual_remaining_leaves']
                        employee_remaining_leaves += virtual_remaining_leaves\
                            if leave_type.request_unit in ['day', 'half_day']\
                            else virtual_remaining_leaves / (employee.resource_calendar_id.hours_per_day or HOURS_PER_DAY)
            employee.allocation_remaining_display = "%g" % float_round(employee_remaining_leaves, precision_digits=2)

    def _compute_presence_state(self):
        super()._compute_presence_state()
        employees = self.filtered(lambda employee: employee.hr_presence_state != 'present' and employee.is_absent)
        employees.update({'hr_presence_state': 'absent'})

    def _compute_presence_icon(self):
        super()._compute_presence_icon()
        employees_absent = self.filtered(lambda employee:
                                         employee.hr_presence_state != 'present'
                                         and employee.is_absent)
        employees_absent.update({'hr_icon_display': 'presence_holiday_absent'})
        employees_present = self.filtered(lambda employee:
                                          employee.hr_presence_state == 'present'
                                          and employee.is_absent)
        employees_present.update({'hr_icon_display': 'presence_holiday_present'})

    def _compute_leave_status(self):
        # Used SUPERUSER_ID to forcefully get status of other user's leave, to bypass record rule
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('date_from', '<=', fields.Datetime.now()),
            ('date_to', '>=', fields.Datetime.now()),
            ('state', '=', 'validate'),
        ])
        leave_data = {}
        for holiday in holidays:
            leave_data[holiday.employee_id.id] = {}
            leave_data[holiday.employee_id.id]['leave_date_from'] = holiday.date_from.date()
            leave_data[holiday.employee_id.id]['leave_date_to'] = holiday.date_to.date()
            leave_data[holiday.employee_id.id]['current_leave_state'] = holiday.state

        for employee in self:
            employee.leave_date_from = leave_data.get(employee.id, {}).get('leave_date_from')
            employee.leave_date_to = leave_data.get(employee.id, {}).get('leave_date_to')
            employee.current_leave_state = leave_data.get(employee.id, {}).get('current_leave_state')
            employee.is_absent = leave_data.get(employee.id) and leave_data.get(employee.id, {}).get('current_leave_state') in ['validate']

    @api.depends('parent_id')
    def _compute_leave_manager(self):
        for employee in self:
            previous_manager = employee._origin.parent_id.user_id
            manager = employee.parent_id.user_id
            if manager and employee.leave_manager_id == previous_manager or not employee.leave_manager_id:
                employee.leave_manager_id = manager
            elif not employee.leave_manager_id:
                employee.leave_manager_id = False

    def _compute_show_leaves(self):
        show_leaves = self.env['res.users'].has_group('hr_holidays.group_hr_holidays_user')
        for employee in self:
            if show_leaves or employee.user_id == self.env.user:
                employee.show_leaves = True
            else:
                employee.show_leaves = False

    def _search_absent_employee(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        # This search is only used for the 'Absent Today' filter however
        # this only returns employees that are absent right now.
        today_date = datetime.datetime.utcnow().date()
        today_start = fields.Datetime.to_string(today_date)
        today_end = fields.Datetime.to_string(today_date + relativedelta(hours=23, minutes=59, seconds=59))
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', '!=', False),
            ('state', '=', 'validate'),
            ('date_from', '<=', today_end),
            ('date_to', '>=', today_start),
        ])
        operator = ['in', 'not in'][(operator == '=') != value]
        return [('id', operator, holidays.mapped('employee_id').ids)]

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('salary_simulation'):
            return super().create(vals_list)
        approver_group = self.env.ref('hr_holidays.group_hr_holidays_responsible', raise_if_not_found=False)
        group_updates = []
        for vals in vals_list:
            if 'parent_id' in vals:
                manager = self.env['hr.employee'].browse(vals['parent_id']).user_id
                vals['leave_manager_id'] = vals.get('leave_manager_id', manager.id)
            if approver_group and vals.get('leave_manager_id'):
                group_updates.append((4, vals['leave_manager_id']))
        if group_updates:
            approver_group.sudo().write({'users': group_updates})
        return super().create(vals_list)

    def write(self, values):
        if 'parent_id' in values:
            manager = self.env['hr.employee'].browse(values['parent_id']).user_id
            if manager:
                to_change = self.filtered(lambda e: e.leave_manager_id == e.parent_id.user_id or not e.leave_manager_id)
                to_change.write({'leave_manager_id': values.get('leave_manager_id', manager.id)})

        old_managers = self.env['res.users']
        if 'leave_manager_id' in values:
            old_managers = self.mapped('leave_manager_id')
            if values['leave_manager_id']:
                leave_manager = self.env['res.users'].browse(values['leave_manager_id'])
                old_managers -= leave_manager
                approver_group = self.env.ref('hr_holidays.group_hr_holidays_responsible', raise_if_not_found=False)
                if approver_group and not leave_manager.has_group('hr_holidays.group_hr_holidays_responsible'):
                    leave_manager.sudo().write({'groups_id': [(4, approver_group.id)]})

        res = super(HrEmployeeBase, self).write(values)
        # remove users from the Responsible group if they are no longer leave managers
        old_managers.sudo()._clean_leave_responsible_users()

        if 'parent_id' in values or 'department_id' in values:
            today_date = fields.Datetime.now()
            hr_vals = {}
            if values.get('parent_id') is not None:
                hr_vals['manager_id'] = values['parent_id']
            if values.get('department_id') is not None:
                hr_vals['department_id'] = values['department_id']
            holidays = self.env['hr.leave'].sudo().search(['|', ('state', 'in', ['draft', 'confirm']), ('date_from', '>', today_date), ('employee_id', 'in', self.ids)])
            holidays.write(hr_vals)
            allocations = self.env['hr.leave.allocation'].sudo().search([('state', 'in', ['draft', 'confirm']), ('employee_id', 'in', self.ids)])
            allocations.write(hr_vals)
        return res

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    current_leave_id = fields.Many2one('hr.leave.type', compute='_compute_current_leave', string="Current Time Off Type",
                                       groups="hr.group_hr_user")

    def _compute_current_leave(self):
        self.current_leave_id = False

        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('date_from', '<=', fields.Datetime.now()),
            ('date_to', '>=', fields.Datetime.now()),
            ('state', '=', 'validate'),
        ])
        for holiday in holidays:
            employee = self.filtered(lambda e: e.id == holiday.employee_id.id)
            employee.current_leave_id = holiday.holiday_status_id.id

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return super()._get_user_m2o_to_empty_on_archived_employees() + ['leave_manager_id']

    def action_time_off_dashboard(self):
        return {
            'name': _('Time Off Dashboard'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'views': [[self.env.ref('hr_holidays.hr_leave_employee_view_dashboard').id, 'calendar']],
            'domain': [('employee_id', 'in', self.ids)],
            'context': {
                'employee_id': self.ids,
            },
        }

    def _get_contextual_employee(self):
        if self.env.context.get('employee_id'):
            return self.browse(self.env.context['employee_id'])
        return self.env.user.employee_id

    def _is_leave_user(self):
        return self == self.env.user.employee_id and self.user_has_groups('hr_holidays.group_hr_holidays_user')

    def get_stress_days(self, start_date, end_date):
        all_days = {}

        self = self or self.env.user.employee_id

        stress_days = self._get_stress_days(start_date, end_date)
        for stress_day in stress_days:
            num_days = (stress_day.end_date - stress_day.start_date).days
            for d in range(num_days + 1):
                all_days[str(stress_day.start_date + relativedelta(days=d))] = stress_day.color

        return all_days

    @api.model
    def get_special_days_data(self, date_start, date_end):
        return {
            'stressDays': self.get_stress_days_data(date_start, date_end),
            'bankHolidays': self.get_public_holidays_data(date_start, date_end),
        }

    @api.model
    def get_public_holidays_data(self, date_start, date_end):
        self = self._get_contextual_employee()
        employee_tz = pytz.timezone(self._get_tz() if self else self.env.user.tz or 'utc')
        public_holidays = self._get_public_holidays(date_start, date_end).sorted('date_from')
        return list(map(lambda bh: {
            'id': -bh.id,
            'colorIndex': 0,
            'end': datetime.datetime.combine(bh.date_to.astimezone(employee_tz), datetime.datetime.max.time()).isoformat(),
            'endType': "datetime",
            'isAllDay': True,
            'start': datetime.datetime.combine(bh.date_from.astimezone(employee_tz), datetime.datetime.min.time()).isoformat(),
            'startType': "datetime",
            'title': bh.name,
        }, public_holidays))

    def _get_public_holidays(self, date_start, date_end):
        domain = [
            ('resource_id', '=', False),
            ('company_id', 'in', self.env.companies.ids),
            ('date_from', '<=', date_end),
            ('date_to', '>=', date_start),
        ]

        # a user with hr_holidays permissions will be able to see all public holidays from his calendar
        if not self._is_leave_user():
            domain += [
                '|',
                ('calendar_id', '=', False),
                ('calendar_id', '=', self.resource_calendar_id.id),
            ]

        return self.env['resource.calendar.leaves'].search(domain)

    @api.model
    def get_stress_days_data(self, date_start, date_end):
        self = self._get_contextual_employee()
        stress_days = self._get_stress_days(date_start, date_end).sorted('start_date')
        return list(map(lambda sd: {
            'id': -sd.id,
            'colorIndex': sd.color,
            'end': datetime.datetime.combine(sd.end_date, datetime.datetime.max.time()).isoformat(),
            'endType': "datetime",
            'isAllDay': True,
            'start': datetime.datetime.combine(sd.start_date, datetime.datetime.min.time()).isoformat(),
            'startType': "datetime",
            'title': sd.name,
        }, stress_days))

    def _get_stress_days(self, start_date, end_date):
        domain = [
            ('start_date', '<=', end_date),
            ('end_date', '>=', start_date),
            ('company_id', 'in', self.env.companies.ids),
        ]

        # a user with hr_holidays permissions will be able to see all stress days from his calendar
        if not self._is_leave_user():
            domain += [
                '|',
                ('resource_calendar_id', '=', False),
                ('resource_calendar_id', '=', self.resource_calendar_id.id),
            ]
            if self.department_id:
                domain += [
                    '|',
                    ('department_ids', '=', False),
                    ('department_ids', 'parent_of', self.department_id.id),
                ]
            else:
                domain += [('department_ids', '=', False)]

        return self.env['hr.leave.stress.day'].search(domain)
