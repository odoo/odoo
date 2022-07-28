# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

from collections import defaultdict
import logging

from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.addons.resource.models.resource import HOURS_PER_DAY
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round
from odoo.tools.date_utils import get_timedelta
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class HolidaysAllocation(models.Model):
    """ Allocation Requests Access specifications: similar to leave requests """
    _name = "hr.leave.allocation"
    _description = "Time Off Allocation"
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

    def _default_holiday_status_id(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_user'):
            domain = [('has_valid_allocation', '=', True), ('requires_allocation', '=', 'yes')]
        else:
            domain = [('has_valid_allocation', '=', True), ('requires_allocation', '=', 'yes'), ('employee_requests', '=', 'yes')]
        return self.env['hr.leave.type'].search(domain, limit=1)

    def _domain_holiday_status_id(self):
        if self.user_has_groups('hr_holidays.group_hr_holidays_user'):
            return [('requires_allocation', '=', 'yes')]
        return [('employee_requests', '=', 'yes')]

    name = fields.Char('Description', compute='_compute_description', inverse='_inverse_description', search='_search_description', compute_sudo=False)
    name_validity = fields.Char('Description with validity', compute='_compute_description_validity')
    active = fields.Boolean(default=True)
    private_name = fields.Char('Allocation Description', groups='hr_holidays.group_hr_holidays_user')
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate', 'Approved')
        ], string='Status', readonly=True, tracking=True, copy=False, default='draft',
        help="The status is set to 'To Submit', when an allocation request is created." +
        "\nThe status is 'To Approve', when an allocation request is confirmed by user." +
        "\nThe status is 'Refused', when an allocation request is refused by manager." +
        "\nThe status is 'Approved', when an allocation request is approved by manager.")
    date_from = fields.Date('Start Date', index=True, copy=False, default=fields.Date.context_today,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, tracking=True, required=True)
    date_to = fields.Date('End Date', copy=False, tracking=True,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]})
    holiday_status_id = fields.Many2one(
        "hr.leave.type", compute='_compute_holiday_status_id', store=True, string="Time Off Type", required=True, readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)], 'validate': [('readonly', True)]},
        domain=_domain_holiday_status_id,
        default=_default_holiday_status_id)
    employee_id = fields.Many2one(
        'hr.employee', compute='_compute_from_employee_ids', store=True, string='Employee', index=True, readonly=False, ondelete="restrict", tracking=True,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate': [('readonly', True)]})
    employee_company_id = fields.Many2one(related='employee_id.company_id', readonly=True, store=True)
    active_employee = fields.Boolean('Active Employee', related='employee_id.active', readonly=True)
    manager_id = fields.Many2one('hr.employee', compute='_compute_manager_id', store=True, string='Manager')
    notes = fields.Text('Reasons', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    # duration
    number_of_days = fields.Float(
        'Number of Days', compute='_compute_from_holiday_status_id', store=True, readonly=False, tracking=True, default=1,
        help='Duration in days. Reference field to use when necessary.')
    number_of_days_display = fields.Float(
        'Duration (days)', compute='_compute_number_of_days_display',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help="If Accrual Allocation: Number of days allocated in addition to the ones you will get via the accrual' system.")
    number_of_hours_display = fields.Float(
        'Duration (hours)', compute='_compute_number_of_hours_display',
        help="If Accrual Allocation: Number of hours allocated in addition to the ones you will get via the accrual' system.")
    duration_display = fields.Char('Allocated (Days/Hours)', compute='_compute_duration_display',
        help="Field allowing to see the allocation duration in days or hours depending on the type_request_unit")
    # details
    parent_id = fields.Many2one('hr.leave.allocation', string='Parent')
    linked_request_ids = fields.One2many('hr.leave.allocation', 'parent_id', string='Linked Requests')
    approver_id = fields.Many2one(
        'hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validates the allocation')
    validation_type = fields.Selection(string='Validation Type', related='holiday_status_id.allocation_validation_type', readonly=True)
    can_reset = fields.Boolean('Can reset', compute='_compute_can_reset')
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    type_request_unit = fields.Selection(related='holiday_status_id.request_unit', readonly=True)
    # mode
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag')],
        string='Allocation Mode', readonly=True, required=True, default='employee',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        help="Allow to create requests in batchs:\n- By Employee: for a specific employee"
             "\n- By Company: all employees of the specified company"
             "\n- By Department: all employees of the specified department"
             "\n- By Employee Tag: all employees of the specific employee group category")
    employee_ids = fields.Many2many(
        'hr.employee', compute='_compute_from_holiday_type', store=True, string='Employees', readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate': [('readonly', True)]})
    multi_employee = fields.Boolean(
        compute='_compute_from_employee_ids', store=True,
        help='Holds whether this allocation concerns more than 1 employee')
    mode_company_id = fields.Many2one(
        'res.company', compute='_compute_from_holiday_type', store=True, string='Company Mode', readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate': [('readonly', True)]})
    department_id = fields.Many2one(
        'hr.department', compute='_compute_department_id', store=True, string='Department',
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    category_id = fields.Many2one(
        'hr.employee.category', compute='_compute_from_holiday_type', store=True, string='Employee Tag', readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate': [('readonly', True)]})
    # accrual configuration
    lastcall = fields.Date("Date of the last accrual allocation", readonly=True, default=fields.Date.context_today)
    nextcall = fields.Date("Date of the next accrual allocation", default=False, readonly=True)
    allocation_type = fields.Selection(
        [
            ('regular', 'Regular Allocation'),
            ('accrual', 'Accrual Allocation')
        ], string="Allocation Type", default="regular", required=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    is_officer = fields.Boolean(compute='_compute_is_officer')
    accrual_plan_id = fields.Many2one('hr.leave.accrual.plan', compute="_compute_from_holiday_status_id", store=True, readonly=False, domain="['|', ('time_off_type_id', '=', False), ('time_off_type_id', '=', holiday_status_id)]", tracking=True)
    max_leaves = fields.Float(compute='_compute_leaves')
    leaves_taken = fields.Float(compute='_compute_leaves')
    taken_leave_ids = fields.One2many('hr.leave', 'holiday_allocation_id', domain="[('state', 'in', ['confirm', 'validate1', 'validate'])]")

    _sql_constraints = [
        ('type_value',
         "CHECK( (holiday_type='employee' AND (employee_id IS NOT NULL OR multi_employee IS TRUE)) or "
         "(holiday_type='category' AND category_id IS NOT NULL) or "
         "(holiday_type='department' AND department_id IS NOT NULL) or "
         "(holiday_type='company' AND mode_company_id IS NOT NULL))",
         "The employee, department, company or employee category of this request is missing. Please make sure that your user login is linked to an employee."),
        ('duration_check', "CHECK( ( number_of_days > 0 AND allocation_type='regular') or (allocation_type != 'regular'))", "The duration must be greater than 0."),
    ]

    # The compute does not get triggered without a depends on record creation
    # aka keep the 'useless' depends
    @api.depends_context('uid')
    @api.depends('allocation_type')
    def _compute_is_officer(self):
        self.is_officer = self.env.user.has_group("hr_holidays.group_hr_holidays_user")

    @api.depends_context('uid')
    def _compute_description(self):
        self.check_access_rights('read')
        self.check_access_rule('read')

        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')

        for allocation in self:
            if is_officer or allocation.employee_id.user_id == self.env.user or allocation.employee_id.leave_manager_id == self.env.user:
                allocation.name = allocation.sudo().private_name
            else:
                allocation.name = '*****'

    def _inverse_description(self):
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        for allocation in self:
            if is_officer or allocation.employee_id.user_id == self.env.user or allocation.employee_id.leave_manager_id == self.env.user:
                allocation.sudo().private_name = allocation.name

    def _search_description(self, operator, value):
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        domain = [('private_name', operator, value)]

        if not is_officer:
            domain = expression.AND([domain, [('employee_id.user_id', '=', self.env.user.id)]])

        allocations = self.sudo().search(domain)
        return [('id', 'in', allocations.ids)]

    @api.depends('name', 'date_from', 'date_to')
    def _compute_description_validity(self):
        for allocation in self:
            if allocation.date_to:
                name_validity = _("%s (from %s to %s)", allocation.name, allocation.date_from.strftime("%b %d %Y"), allocation.date_to.strftime("%b %d %Y"))
            else:
                name_validity = _("%s (from %s to No Limit)", allocation.name, allocation.date_from.strftime("%b %d %Y"))
            allocation.name_validity = name_validity

    @api.depends('employee_id', 'holiday_status_id', 'taken_leave_ids.number_of_days', 'taken_leave_ids.state')
    def _compute_leaves(self):
        for allocation in self:
            allocation.max_leaves = allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days
            allocation.leaves_taken = sum(taken_leave.number_of_hours_display if taken_leave.leave_type_request_unit == 'hour' else taken_leave.number_of_days\
                for taken_leave in allocation.taken_leave_ids\
                if taken_leave.state == 'validate')

    @api.depends('number_of_days')
    def _compute_number_of_days_display(self):
        for allocation in self:
            allocation.number_of_days_display = allocation.number_of_days

    @api.depends('number_of_days', 'employee_id')
    def _compute_number_of_hours_display(self):
        for allocation in self:
            if allocation.parent_id and allocation.parent_id.type_request_unit == "hour":
                allocation.number_of_hours_display = allocation.number_of_days * HOURS_PER_DAY
            elif allocation.number_of_days:
                allocation.number_of_hours_display = allocation.number_of_days * (allocation.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
            else:
                allocation.number_of_hours_display = 0.0

    @api.depends('number_of_hours_display', 'number_of_days_display')
    def _compute_duration_display(self):
        for allocation in self:
            allocation.duration_display = '%g %s' % (
                (float_round(allocation.number_of_hours_display, precision_digits=2)
                if allocation.type_request_unit == 'hour'
                else float_round(allocation.number_of_days_display, precision_digits=2)),
                _('hours') if allocation.type_request_unit == 'hour' else _('days'))

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_reset(self):
        for allocation in self:
            try:
                allocation._check_approval_update('draft')
            except (AccessError, UserError):
                allocation.can_reset = False
            else:
                allocation.can_reset = True

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        for allocation in self:
            try:
                if allocation.state == 'confirm' and allocation.validation_type != 'no':
                    allocation._check_approval_update('validate')
            except (AccessError, UserError):
                allocation.can_approve = False
            else:
                allocation.can_approve = True

    @api.depends('employee_ids')
    def _compute_from_employee_ids(self):
        for allocation in self:
            if len(allocation.employee_ids) == 1:
                allocation.employee_id = allocation.employee_ids[0]._origin
            else:
                allocation.employee_id = False
            allocation.multi_employee = (len(allocation.employee_ids) > 1)

    @api.depends('holiday_type')
    def _compute_from_holiday_type(self):
        default_employee_ids = self.env['hr.employee'].browse(self.env.context.get('default_employee_id')) or self.env.user.employee_id
        for allocation in self:
            if allocation.holiday_type == 'employee':
                if not allocation.employee_ids:
                    allocation.employee_ids = self.env.user.employee_id
                allocation.mode_company_id = False
                allocation.category_id = False
            elif allocation.holiday_type == 'company':
                allocation.employee_ids = False
                if not allocation.mode_company_id:
                    allocation.mode_company_id = self.env.company
                allocation.category_id = False
            elif allocation.holiday_type == 'department':
                allocation.employee_ids = False
                allocation.mode_company_id = False
                allocation.category_id = False
            elif allocation.holiday_type == 'category':
                allocation.employee_ids = False
                allocation.mode_company_id = False
            else:
                allocation.employee_ids = default_employee_ids

    @api.depends('holiday_type', 'employee_id')
    def _compute_department_id(self):
        for allocation in self:
            if allocation.holiday_type == 'employee':
                allocation.department_id = allocation.employee_id.department_id
            elif allocation.holiday_type == 'department':
                if not allocation.department_id:
                    allocation.department_id = self.env.user.employee_id.department_id
            elif allocation.holiday_type == 'category':
                allocation.department_id = False

    @api.depends('employee_id')
    def _compute_manager_id(self):
        for allocation in self:
            allocation.manager_id = allocation.employee_id and allocation.employee_id.parent_id

    @api.depends('accrual_plan_id')
    def _compute_holiday_status_id(self):
        default_holiday_status_id = None
        for holiday in self:
            if not holiday.holiday_status_id:
                if holiday.accrual_plan_id:
                    holiday.holiday_status_id = holiday.accrual_plan_id.time_off_type_id
                else:
                    if not default_holiday_status_id:  # fetch when we need it
                        default_holiday_status_id = self._default_holiday_status_id()
                    holiday.holiday_status_id = default_holiday_status_id

    @api.depends('holiday_status_id', 'allocation_type', 'number_of_hours_display', 'number_of_days_display', 'date_to')
    def _compute_from_holiday_status_id(self):
        accrual_allocations = self.filtered(lambda alloc: alloc.allocation_type == 'accrual' and not alloc.accrual_plan_id and alloc.holiday_status_id)
        accruals_dict = {}
        if accrual_allocations:
            accruals_read_group = self.env['hr.leave.accrual.plan'].read_group(
                [('time_off_type_id', 'in', accrual_allocations.holiday_status_id.ids)],
                ['time_off_type_id', 'ids:array_agg(id)'],
                ['time_off_type_id'],
            )
            accruals_dict = {res['time_off_type_id'][0]: res['ids'] for res in accruals_read_group}
        for allocation in self:
            allocation.number_of_days = allocation.number_of_days_display
            if allocation.type_request_unit == 'hour':
                allocation.number_of_days = allocation.number_of_hours_display / (allocation.employee_id.sudo().resource_calendar_id.hours_per_day or HOURS_PER_DAY)
            if allocation.accrual_plan_id.time_off_type_id.id not in (False, allocation.holiday_status_id.id):
                allocation.accrual_plan_id = False
            if allocation.allocation_type == 'accrual' and not allocation.accrual_plan_id:
                if allocation.holiday_status_id:
                    allocation.accrual_plan_id = accruals_dict.get(allocation.holiday_status_id.id, [False])[0]

    def _end_of_year_accrual(self):
        # to override in payroll
        first_day_this_year = fields.Date.today() + relativedelta(month=1, day=1)
        for allocation in self:
            current_level = allocation._get_current_accrual_plan_level_id(first_day_this_year)[0]
            nextcall = current_level._get_next_date(first_day_this_year)
            if current_level and current_level.action_with_unused_accruals == 'lost':
                # Allocations are lost but number_of_days should not be lower than leaves_taken
                allocation.write({'number_of_days': allocation.leaves_taken, 'lastcall': first_day_this_year, 'nextcall': nextcall})

    def _get_current_accrual_plan_level_id(self, date, level_ids=False):
        """
        Returns a pair (accrual_plan_level, idx) where accrual_plan_level is the level for the given date
         and idx is the index for the plan in the ordered set of levels
        """
        self.ensure_one()
        if not self.accrual_plan_id.level_ids:
            return (False, False)
        # Sort by sequence which should be equivalent to the level
        if not level_ids:
            level_ids = self.accrual_plan_id.level_ids.sorted('sequence')
        current_level = False
        current_level_idx = -1
        for idx, level in enumerate(level_ids):
            if date > self.date_from + get_timedelta(level.start_count, level.start_type):
                current_level = level
                current_level_idx = idx
        # If transition_mode is set to `immediately` or we are currently on the first level
        # the current_level is simply the first level in the list.
        if current_level_idx <= 0 or self.accrual_plan_id.transition_mode == "immediately":
            return (current_level, current_level_idx)
        # In this case we have to verify that the 'previous level' is not the current one due to `end_of_accrual`
        level_start_date = self.date_from + get_timedelta(current_level.start_count, current_level.start_type)
        previous_level = level_ids[current_level_idx - 1]
        # If the next date from the current level's start date is before the last call of the previous level
        # return the previous level
        if current_level._get_next_date(level_start_date) < previous_level._get_next_date(level_start_date):
            return (previous_level, current_level_idx - 1)
        return (current_level, current_level_idx)

    def _process_accrual_plan_level(self, level, start_period, start_date, end_period, end_date):
        """
        Returns the added days for that level
        """
        self.ensure_one()
        if level.is_based_on_worked_time:
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            worked = self.employee_id._get_work_days_data_batch(start_dt, end_dt, calendar=self.employee_id.resource_calendar_id)\
                [self.employee_id.id]['hours']
            left = self.employee_id.sudo()._get_leave_days_data_batch(start_dt, end_dt,
                domain=[('time_type', '=', 'leave')])[self.employee_id.id]['hours']
            work_entry_prorata = worked / (left + worked) if worked else 0
            added_value = work_entry_prorata * level.added_value
        else:
            added_value = level.added_value
        # Convert time in hours to time in days in case the level is encoded in hours
        if level.added_value_type == 'hours':
            added_value = added_value / (self.employee_id.sudo().resource_id.calendar_id.hours_per_day or HOURS_PER_DAY)
        period_prorata = 1
        if start_period != start_date or end_period != end_date:
            period_days = (end_period - start_period)
            call_days = (end_date - start_date)
            period_prorata = min(1, call_days / period_days) if period_days else 1
        return added_value * period_prorata

    def _process_accrual_plans(self):
        """
        This method is part of the cron's process.
        The goal of this method is to retroactively apply accrual plan levels and progress from nextcall to today
        """
        today = fields.Date.today()
        first_allocation = _("""This allocation have already ran once, any modification won't be effective to the days allocated to the employee. If you need to change the configuration of the allocation, cancel and create a new one.""")
        for allocation in self:
            level_ids = allocation.accrual_plan_id.level_ids.sorted('sequence')
            if not level_ids:
                continue
            if not allocation.nextcall:
                first_level = level_ids[0]
                first_level_start_date = allocation.date_from + get_timedelta(first_level.start_count, first_level.start_type)
                if today < first_level_start_date:
                    # Accrual plan is not configured properly or has not started
                    continue
                allocation.lastcall = max(allocation.lastcall, first_level_start_date)
                allocation.nextcall = first_level._get_next_date(allocation.lastcall)
                if len(level_ids) > 1:
                    second_level_start_date = allocation.date_from + get_timedelta(level_ids[1].start_count, level_ids[1].start_type)
                    allocation.nextcall = min(second_level_start_date, allocation.nextcall)
                allocation._message_log(body=first_allocation)
            days_added_per_level = defaultdict(lambda: 0)
            while allocation.nextcall <= today:
                (current_level, current_level_idx) = allocation._get_current_accrual_plan_level_id(allocation.nextcall)
                nextcall = current_level._get_next_date(allocation.nextcall)
                # Since _get_previous_date returns the given date if it corresponds to a call date
                # this will always return lastcall except possibly on the first call
                # this is used to prorate the first number of days given to the employee
                period_start = current_level._get_previous_date(allocation.lastcall)
                period_end = current_level._get_next_date(allocation.lastcall)
                # If accruals are lost at the beginning of year, skip accrual until beginning of this year
                if current_level.action_with_unused_accruals == 'lost':
                    this_year_first_day = today + relativedelta(day=1, month=1)
                    if period_end < this_year_first_day:
                        allocation.lastcall = allocation.nextcall
                        allocation.nextcall = nextcall
                        continue
                    else:
                        period_start = max(period_start, this_year_first_day)
                # Also prorate this accrual in the event that we are passing from one level to another
                if current_level_idx < (len(level_ids) - 1) and allocation.accrual_plan_id.transition_mode == 'immediately':
                    next_level = level_ids[current_level_idx + 1]
                    current_level_last_date = allocation.date_from + get_timedelta(next_level.start_count, next_level.start_type)
                    if allocation.nextcall != current_level_last_date:
                        nextcall = min(nextcall, current_level_last_date)
                days_added_per_level[current_level] += allocation._process_accrual_plan_level(
                    current_level, period_start, allocation.lastcall, period_end, allocation.nextcall)
                allocation.lastcall = allocation.nextcall
                allocation.nextcall = nextcall
            if days_added_per_level:
                number_of_days_to_add = allocation.number_of_days + sum(days_added_per_level.values())
                # Let's assume the limit of the last level is the correct one
                allocation.number_of_days = min(number_of_days_to_add, current_level.maximum_leave + allocation.leaves_taken) if current_level.maximum_leave > 0 else number_of_days_to_add

    @api.model
    def _update_accrual(self):
        """
            Method called by the cron task in order to increment the number_of_days when
            necessary.
        """
        # Get the current date to determine the start and end of the accrual period
        today = datetime.combine(fields.Date.today(), time(0, 0, 0))
        this_year_first_day = today + relativedelta(day=1, month=1)
        end_of_year_allocations = self.search(
        [('allocation_type', '=', 'accrual'), ('state', '=', 'validate'), ('accrual_plan_id', '!=', False), ('employee_id', '!=', False),
            '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()), ('lastcall', '<', this_year_first_day)])
        end_of_year_allocations._end_of_year_accrual()
        end_of_year_allocations.flush()
        allocations = self.search(
        [('allocation_type', '=', 'accrual'), ('state', '=', 'validate'), ('accrual_plan_id', '!=', False), ('employee_id', '!=', False),
            '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()),
            '|', ('nextcall', '=', False), ('nextcall', '<=', today)])
        allocations._process_accrual_plans()

    ####################################################
    # ORM Overrides methods
    ####################################################

    def name_get(self):
        res = []
        for allocation in self:
            if allocation.holiday_type == 'company':
                target = allocation.mode_company_id.name
            elif allocation.holiday_type == 'department':
                target = allocation.department_id.name
            elif allocation.holiday_type == 'category':
                target = allocation.category_id.name
            elif allocation.employee_id:
                target = allocation.employee_id.name
            else:
                target = ', '.join(allocation.employee_ids.sudo().mapped('name'))

            res.append(
                (allocation.id,
                 _("Allocation of %(allocation_name)s : %(duration).2f %(duration_type)s to %(person)s",
                   allocation_name=allocation.holiday_status_id.sudo().name,
                   duration=allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days,
                   duration_type=_('hours') if allocation.type_request_unit == 'hour' else _('days'),
                   person=target
                ))
            )
        return res

    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe(partner_ids=employee.user_id.partner_id.ids)

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to avoid automatic logging of creation """
        for values in vals_list:
            employee_id = values.get('employee_id', False)
            if not values.get('department_id'):
                values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
            # default `lastcall` to `nextcall`
            if 'date_from' in values and 'lastcall' not in values:
                values['lastcall'] = values['date_from']
        holidays = super(HolidaysAllocation, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        for holiday in holidays:
            partners_to_subscribe = set()
            if holiday.employee_id.user_id:
                partners_to_subscribe.add(holiday.employee_id.user_id.partner_id.id)
            if holiday.validation_type == 'officer':
                partners_to_subscribe.add(holiday.employee_id.parent_id.user_id.partner_id.id)
                partners_to_subscribe.add(holiday.employee_id.leave_manager_id.partner_id.id)
            holiday.message_subscribe(partner_ids=tuple(partners_to_subscribe))
            if not self._context.get('import_file'):
                holiday.activity_update()
            if holiday.validation_type == 'no':
                if holiday.state == 'draft':
                    holiday.action_confirm()
                    holiday.action_validate()
        return holidays

    def write(self, values):
        employee_id = values.get('employee_id', False)
        if values.get('state'):
            self._check_approval_update(values['state'])
        result = super(HolidaysAllocation, self).write(values)
        self.add_follower(employee_id)
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_correct_states(self):
        state_description_values = {elem[0]: elem[1] for elem in self._fields['state']._description_selection(self.env)}
        for holiday in self.filtered(lambda holiday: holiday.state not in ['draft', 'cancel', 'confirm']):
            raise UserError(_('You cannot delete an allocation request which is in %s state.') % (state_description_values.get(holiday.state),))

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_leaves(self):
        if any(allocation.holiday_status_id.requires_allocation == 'yes' and allocation.leaves_taken > 0 for allocation in self):
            raise UserError(_('You cannot delete an allocation request which has some validated leaves.'))

    def _get_mail_redirect_suggested_company(self):
        return self.holiday_status_id.company_id

    ####################################################
    # Business methods
    ####################################################

    def _prepare_holiday_values(self, employees):
        self.ensure_one()
        return [{
            'name': self.name,
            'holiday_type': 'employee',
            'holiday_status_id': self.holiday_status_id.id,
            'notes': self.notes,
            'number_of_days': self.number_of_days,
            'parent_id': self.id,
            'employee_id': employee.id,
            'employee_ids': [(6, 0, [employee.id])],
            'state': 'confirm',
            'allocation_type': self.allocation_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'accrual_plan_id': self.accrual_plan_id.id,
        } for employee in employees]

    def action_draft(self):
        if any(holiday.state not in ['confirm', 'refuse'] for holiday in self):
            raise UserError(_('Allocation request state must be "Refused" or "To Approve" in order to be reset to Draft.'))
        self.write({
            'state': 'draft',
            'approver_id': False,
        })
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_draft()
            linked_requests.unlink()
        self.activity_update()
        return True

    def action_confirm(self):
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Allocation request must be in Draft state ("To Submit") in order to confirm it.'))
        res = self.write({'state': 'confirm'})
        self.activity_update()
        return res

    def action_validate(self):
        current_employee = self.env.user.employee_id
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Allocation request must be confirmed in order to approve it.'))

        self.write({
            'state': 'validate',
            'approver_id': current_employee.id
        })

        for holiday in self:
            holiday._action_validate_create_childs()
        self.activity_update()
        return True

    def _action_validate_create_childs(self):
        childs = self.env['hr.leave.allocation']
        # In the case we are in holiday_type `employee` and there is only one employee we can keep the same allocation
        # Otherwise we do need to create an allocation for all employees to have a behaviour that is in line
        # with the other holiday_type
        if self.state == 'validate' and (self.holiday_type in ['category', 'department', 'company'] or
            (self.holiday_type == 'employee' and len(self.employee_ids) > 1)):
            if self.holiday_type == 'employee':
                employees = self.employee_ids
            elif self.holiday_type == 'category':
                employees = self.category_id.employee_ids
            elif self.holiday_type == 'department':
                employees = self.department_id.member_ids
            else:
                employees = self.env['hr.employee'].search([('company_id', '=', self.mode_company_id.id)])

            allocation_create_vals = self._prepare_holiday_values(employees)
            childs += self.with_context(
                mail_notify_force_send=False,
                mail_activity_automation_skip=True
            ).create(allocation_create_vals)
            if childs:
                childs.action_validate()
        return childs

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Allocation request must be confirmed or validated in order to refuse it.'))

        self.write({'state': 'refuse', 'approver_id': current_employee.id})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()
        self.activity_update()
        return True

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return
        current_employee = self.env.user.employee_id
        if not current_employee:
            return
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')
        for holiday in self:
            val_type = holiday.holiday_status_id.sudo().allocation_validation_type
            if state == 'confirm':
                continue

            if state == 'draft':
                if holiday.employee_id != current_employee and not is_manager:
                    raise UserError(_('Only a time off Manager can reset other people allocation.'))
                continue

            if not is_officer and self.env.user != holiday.employee_id.leave_manager_id and not val_type == 'no':
                raise UserError(_('Only a time off Officer/Responsible or Manager can approve or refuse time off requests.'))

            if is_officer or self.env.user == holiday.employee_id.leave_manager_id:
                # use ir.rule based first access check: department, members, ... (see security.xml)
                holiday.check_access_rule('write')

            if holiday.employee_id == current_employee and not is_manager and not val_type == 'no':
                raise UserError(_('Only a time off Manager can approve its own requests.'))

    @api.onchange('allocation_type')
    def _onchange_allocation_type(self):
        if self.allocation_type == 'accrual':
            self.number_of_days = 0.0
        elif not self.number_of_days_display:
            self.number_of_days = 1.0

    # ------------------------------------------------------------
    # Activity methods
    # ------------------------------------------------------------

    def _get_responsible_for_approval(self):
        self.ensure_one()
        responsible = self.env.user

        if self.validation_type == 'officer' or self.validation_type == 'set':
            if self.holiday_status_id.responsible_id:
                responsible = self.holiday_status_id.responsible_id

        return responsible

    def activity_update(self):
        to_clean, to_do = self.env['hr.leave.allocation'], self.env['hr.leave.allocation']
        for allocation in self:
            note = _(
                'New Allocation Request created by %(user)s: %(count)s Days of %(allocation_type)s',
                user=allocation.create_uid.name,
                count=allocation.number_of_days,
                allocation_type=allocation.holiday_status_id.name
            )
            if allocation.state == 'draft':
                to_clean |= allocation
            elif allocation.state == 'confirm':
                allocation.activity_schedule(
                    'hr_holidays.mail_act_leave_allocation_approval',
                    note=note,
                    user_id=allocation.sudo()._get_responsible_for_approval().id or self.env.user.id)
            elif allocation.state == 'validate1':
                allocation.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval'])
                allocation.activity_schedule(
                    'hr_holidays.mail_act_leave_allocation_second_approval',
                    note=note,
                    user_id=allocation.sudo()._get_responsible_for_approval().id or self.env.user.id)
            elif allocation.state == 'validate':
                to_do |= allocation
            elif allocation.state == 'refuse':
                to_clean |= allocation
        if to_clean:
            to_clean.activity_unlink(['hr_holidays.mail_act_leave_allocation_approval', 'hr_holidays.mail_act_leave_allocation_second_approval'])
        if to_do:
            to_do.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval', 'hr_holidays.mail_act_leave_allocation_second_approval'])

    ####################################################
    # Messaging methods
    ####################################################

    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            allocation_notif_subtype_id = self.holiday_status_id.allocation_notif_subtype_id
            return allocation_notif_subtype_id or self.env.ref('hr_holidays.mt_leave_allocation')
        return super(HolidaysAllocation, self)._track_subtype(init_values)

    def _notify_get_groups(self, msg_vals=None):
        """ Handle HR users and officers recipients that can validate or refuse holidays
        directly from email. """
        groups = super(HolidaysAllocation, self)._notify_get_groups(msg_vals=msg_vals)
        local_msg_vals = dict(msg_vals or {})

        self.ensure_one()
        hr_actions = []
        if self.state == 'confirm':
            app_action = self._notify_get_action_link('controller', controller='/allocation/validate', **local_msg_vals)
            hr_actions += [{'url': app_action, 'title': _('Approve')}]
        if self.state in ['confirm', 'validate', 'validate1']:
            ref_action = self._notify_get_action_link('controller', controller='/allocation/refuse', **local_msg_vals)
            hr_actions += [{'url': ref_action, 'title': _('Refuse')}]

        holiday_user_group_id = self.env.ref('hr_holidays.group_hr_holidays_user').id
        new_group = (
            'group_hr_holidays_user', lambda pdata: pdata['type'] == 'user' and holiday_user_group_id in pdata['groups'], {
                'actions': hr_actions,
            })

        return [new_group] + groups

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        # due to record rule can not allow to add follower and mention on validated leave so subscribe through sudo
        if self.state in ['validate', 'validate1']:
            self.check_access_rights('read')
            self.check_access_rule('read')
            return super(HolidaysAllocation, self.sudo()).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)
        return super(HolidaysAllocation, self).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)
