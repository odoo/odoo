# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)
from calendar import monthrange
from datetime import datetime, date, time
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import format_date
from odoo.addons.hr_holidays.models.hr_leave import get_employee_from_context
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools.float_utils import float_round
from odoo.tools.date_utils import get_timedelta


class HrLeaveAllocation(models.Model):
    """ Allocation Requests Access specifications: similar to leave requests """
    _name = 'hr.leave.allocation'
    _description = "Time Off Allocation"
    _order = "create_date desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

    def _default_holiday_status_id(self):
        if self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            domain = [('has_valid_allocation', '=', True), ('requires_allocation', '=', True)]
        else:
            domain = [('has_valid_allocation', '=', True), ('requires_allocation', '=', True), ('employee_requests', '=', True)]
        return self.env['hr.leave.type'].search(domain, limit=1)

    def _domain_holiday_status_id(self):
        domain = [
            ('company_id', 'in', self.env.companies.ids + [False]),
            ('requires_allocation', '=', True),
        ]
        if self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            return domain
        return Domain.AND([domain, [('employee_requests', '=', True)]])

    def _domain_employee_id(self):
        domain = [('company_id', 'in', self.env.companies.ids)]
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            domain += [
                ('leave_manager_id', '=', self.env.user.id)
            ]
        return domain

    name = fields.Char(
        string='Description',
        compute='_compute_description',
        store=True,
        readonly=False,
        compute_sudo=False)
    is_name_custom = fields.Boolean(readonly=True, store=False)
    name_validity = fields.Char('Description with validity', compute='_compute_description_validity')
    state = fields.Selection([
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved'),
        ], string='Status', default='confirm', tracking=True, copy=False, readonly=True,
        help="The status is 'To Approve', when an allocation request is created."
        "\nThe status is 'Refused', when an allocation request is refused by manager."
        "\nThe status is 'Approved', when an allocation request is approved by manager.")
    date_from = fields.Date('Start Date', index=True, copy=False, default=fields.Date.context_today,
        tracking=True, required=True)
    date_to = fields.Date('End Date', copy=False, tracking=True)
    holiday_status_id = fields.Many2one(
        "hr.leave.type", compute='_compute_holiday_status_id', store=True, string="Time Off Type", required=True, readonly=False,
        domain=_domain_holiday_status_id,
        default=_default_holiday_status_id)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', default=lambda self: self.env.user.employee_id,
        index=True, ondelete="restrict", required=True, tracking=True, domain=_domain_employee_id)
    employee_company_id = fields.Many2one(related='employee_id.company_id', readonly=True, store=True)
    active_employee = fields.Boolean('Active Employee', related='employee_id.active', readonly=True)
    manager_id = fields.Many2one('hr.employee', compute='_compute_manager_id', store=True, string='Manager')
    notes = fields.Text('Reasons', readonly=False)
    # duration
    number_of_days = fields.Float(
        'Number of Days', compute='_compute_number_of_days', store=True, readonly=False, tracking=True, default=1,
        help='Duration in days. Reference field to use when necessary.')
    number_of_days_display = fields.Float(
        'Duration (days)', compute='_compute_number_of_days_display',
        help="For an Accrual Allocation, this field contains the theorical amount of time given to the employee, due to a previous start date, on the first run of the plan. This can be manually edited.")
    number_of_hours_display = fields.Float(
        'Duration (hours)', default_export_compatible=True, compute='_compute_number_of_hours_display', store=True,
        help="For an Accrual Allocation, this field contains the theorical amount of time given to the employee, due to a previous start date, on the first run of the plan. This can be manually edited.")
    duration_display = fields.Char('Allocated (Days/Hours)', compute='_compute_duration_display',
        help="Field allowing to see the allocation duration in days or hours depending on the type_request_unit")
    last_executed_carryover_date = fields.Date(export_string_translation=False)
    # details
    approver_id = fields.Many2one(
        'hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validates the allocation')
    second_approver_id = fields.Many2one(
        'hr.employee', string='Second Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validates the allocation with second level (If time off type need second validation)')
    validation_type = fields.Selection(string='Validation Type', related='holiday_status_id.allocation_validation_type', readonly=True)
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    can_validate = fields.Boolean('Can Validate', compute='_compute_can_validate')
    can_refuse = fields.Boolean('Can Refuse', compute='_compute_can_refuse')
    type_request_unit = fields.Selection([
        ('hour', 'Hours'),
        ('half_day', 'Half-Day'),
        ('day', 'Day'),
    ], compute="_compute_type_request_unit")
    department_id = fields.Many2one('hr.department', compute='_compute_department_id', store=True, string='Department', readonly=False)
    # accrual configuration
    lastcall = fields.Date("Date of the last accrual allocation", readonly=True)
    # lastcall is only updated on accrual date. On other dates such as carryover date,
    # actual_lastcall will store the date of the lastcall of the accrual allocation
    actual_lastcall = fields.Date(export_string_translation=False)
    nextcall = fields.Date("Date of the next accrual allocation", readonly=True, default=False)
    already_accrued = fields.Boolean()
    yearly_accrued_amount = fields.Float(export_string_translation=False)
    allocation_type = fields.Selection([
        ('regular', 'Regular Allocation'),
        ('accrual', 'Accrual Allocation')
    ], string="Allocation Type", default="regular", required=True, readonly=True)
    is_officer = fields.Boolean(compute='_compute_is_officer')
    accrual_plan_id = fields.Many2one('hr.leave.accrual.plan',
        compute="_compute_accrual_plan_id", inverse="_inverse_accrual_plan_id", store=True, index='btree_not_null', readonly=False, tracking=True,
        domain="['|', ('time_off_type_id', '=', False), ('time_off_type_id', '=', holiday_status_id)]")
    max_leaves = fields.Float(compute='_compute_leaves')
    leaves_taken = fields.Float(compute='_compute_leaves', string='Time off Taken')
    virtual_remaining_leaves = fields.Float(compute='_compute_leaves', string='Available Time Off')
    expiring_carryover_days = fields.Float("The number of carried over days that will expire on carried_over_days_expiration_date")
    carried_over_days_expiration_date = fields.Date("Carried over days expiration date")
    _duration_check = models.Constraint(
        "CHECK( ( number_of_days > 0 AND allocation_type='regular') or (allocation_type != 'regular'))",
        'The duration must be greater than 0.',
    )

    @api.constrains('date_from', 'date_to')
    def _check_date_from_date_to(self):
        if any(allocation.date_to and allocation.date_from > allocation.date_to for allocation in self):
            raise UserError(_("The Start Date of the Validity Period must be anterior to the End Date."))

    # The compute does not get triggered without a depends on record creation
    # aka keep the 'useless' depends
    @api.depends_context('uid')
    @api.depends('allocation_type')
    def _compute_is_officer(self):
        self.is_officer = self.env.user.has_group("hr_holidays.group_hr_holidays_user")

    def _get_title(self):
        self.ensure_one()
        if not self.holiday_status_id:
            return _("Allocation Request")
        if self.type_request_unit == 'hour':
            return _(
                '%(name)s (%(duration)s hour(s))',
                name=self.holiday_status_id.name,
                duration=self.number_of_days * self.employee_id._get_hours_per_day(self.date_from),
            )
        return _(
            '%(name)s (%(duration)s day(s))',
            name=self.holiday_status_id.name,
            duration=float_round(self.number_of_days, precision_digits=2),
        )

    @api.onchange('name')
    def _onchange_name(self):
        if not self.name:
            self.is_name_custom = False
        elif self.name != self._get_title():
            self.is_name_custom = True

    @api.depends('holiday_status_id', 'number_of_days')
    def _compute_description(self):
        for allocation in self:
            if not allocation.is_name_custom:
                allocation.name = allocation._get_title()

    @api.depends('name', 'date_from', 'date_to')
    def _compute_description_validity(self):
        for allocation in self:
            allocation_date_from = fields.Datetime.to_datetime(allocation.date_from or fields.Date.context_today(allocation))
            allocation_date_to = fields.Datetime.to_datetime(allocation.date_to)

            if allocation.date_to:
                name_validity = self.env._(
                    "%(allocation_name)s (from %(date_from)s to %(date_to)s)",
                    allocation_name=allocation.name,
                    date_from=format_date(allocation.env,
                        fields.Date.context_today(allocation, allocation_date_from),
                    ),
                    date_to=format_date(allocation.env,
                        fields.Date.context_today(allocation, allocation_date_to),
                    ),
                )
            else:
                name_validity = self.env._(
                    "%(allocation_name)s (from %(date_from)s to No Limit)",
                    allocation_name=allocation.name,
                    date_from=format_date(allocation.env,
                        fields.Date.context_today(allocation, allocation_date_from),
                    ),
                )
            allocation.name_validity = name_validity

    @api.depends('employee_id', 'holiday_status_id')
    def _compute_leaves(self):
        date_from = fields.Date.from_string(self.env.context['default_date_from']) if 'default_date_from' in self.env.context else fields.Date.today()
        employee_days_per_allocation = self.employee_id._get_consumed_leaves(self.holiday_status_id, date_from)[0]
        for allocation in self:
            origin = allocation._origin
            virtual_leave = employee_days_per_allocation[origin.employee_id][origin.holiday_status_id][origin]
            allocation.max_leaves = virtual_leave['max_leaves']
            allocation.leaves_taken = virtual_leave['leaves_taken']
            allocation.virtual_remaining_leaves = virtual_leave['virtual_remaining_leaves']

    @api.depends('number_of_days')
    def _compute_number_of_days_display(self):
        for allocation in self:
            allocation.number_of_days_display = allocation.number_of_days

    @api.depends('number_of_days', 'employee_id')
    def _compute_number_of_hours_display(self):
        for allocation in self:
            if not allocation.employee_id:
                continue
            allocation.number_of_hours_display = (allocation.number_of_days * allocation.employee_id._get_hours_per_day(allocation.date_from))

    @api.depends('number_of_hours_display', 'number_of_days_display')
    def _compute_duration_display(self):
        for allocation in self:
            allocation.duration_display = '%g %s' % (
                (float_round(allocation.number_of_hours_display, precision_digits=2)
                if allocation.type_request_unit == 'hour'
                else float_round(allocation.number_of_days_display, precision_digits=2)),
                _('hours') if allocation.type_request_unit == 'hour' else _('days'))

    @api.depends('state', 'employee_id')
    def _compute_can_approve(self):
        for allocation in self:
            allocation.can_approve = allocation._check_approval_update('validate1', raise_if_not_possible=False)

    @api.depends('state', 'employee_id')
    def _compute_can_validate(self):
        for allocation in self:
            allocation.can_validate = allocation._check_approval_update('validate', raise_if_not_possible=False)

    @api.depends('state', 'employee_id')
    def _compute_can_refuse(self):
        for allocation in self:
            allocation.can_refuse = allocation._check_approval_update('refuse', raise_if_not_possible=False)

    @api.depends('employee_id')
    def _compute_department_id(self):
        for allocation in self:
            allocation.department_id = allocation.employee_id.department_id

    @api.depends('employee_id')
    def _compute_manager_id(self):
        for allocation in self:
            allocation.manager_id = allocation.employee_id and allocation.employee_id.parent_id

    @api.depends('accrual_plan_id')
    def _compute_holiday_status_id(self):
        default_holiday_status_id = None
        for allocation in self:
            if not allocation.holiday_status_id:
                if allocation.accrual_plan_id:
                    allocation.holiday_status_id = allocation.accrual_plan_id.time_off_type_id
                else:
                    if not default_holiday_status_id:  # fetch when we need it
                        default_holiday_status_id = self._default_holiday_status_id()
                    allocation.holiday_status_id = default_holiday_status_id

    @api.depends('holiday_status_id', 'number_of_hours_display', 'number_of_days_display', 'type_request_unit', 'employee_id')
    def _compute_number_of_days(self):
        for allocation in self:
            allocation_unit = allocation.type_request_unit
            if allocation_unit != 'hour':
                allocation.number_of_days = allocation.number_of_days_display
            elif allocation_unit == 'hour' and allocation.employee_id:
                allocation.number_of_days = allocation.number_of_hours_display / allocation.employee_id._get_hours_per_day(allocation.date_from)

    @api.depends('holiday_status_id', 'allocation_type')
    def _compute_accrual_plan_id(self):
        accrual_allocations = self.filtered(lambda alloc: alloc.allocation_type == 'accrual' and not alloc.accrual_plan_id and alloc.holiday_status_id)
        accruals_read_group = self.env['hr.leave.accrual.plan']._read_group(
            [('time_off_type_id', 'in', accrual_allocations.holiday_status_id.ids)],
            ['time_off_type_id'],
            ['id:array_agg'],
        )
        accruals_dict = {time_off_type.id: ids for time_off_type, ids in accruals_read_group}
        for allocation in self:
            if (allocation.allocation_type == 'regular' and allocation.accrual_plan_id) or allocation.accrual_plan_id.time_off_type_id.id not in (False, allocation.holiday_status_id.id):
                allocation.accrual_plan_id = False
            if allocation.allocation_type == 'accrual' and not allocation.accrual_plan_id:
                if allocation.holiday_status_id:
                    allocation.accrual_plan_id = accruals_dict.get(allocation.holiday_status_id.id, [False])[0]

    def _inverse_accrual_plan_id(self):
        for allocation in self:
            allocation.allocation_type = "accrual" if allocation.accrual_plan_id else "regular"

    def _get_request_unit(self):
        self.ensure_one()
        if self.allocation_type == "accrual" and self.accrual_plan_id:
            return self.accrual_plan_id.sudo().added_value_type
        elif self.allocation_type == "regular":
            return self.holiday_status_id.request_unit
        else:
            return "day"

    @api.depends("allocation_type", "holiday_status_id", "accrual_plan_id")
    def _compute_type_request_unit(self):
        for allocation in self:
            allocation.type_request_unit = allocation._get_request_unit()

    def _get_carryover_date(self, date_from):
        self.ensure_one()
        carryover_time = self.accrual_plan_id.carryover_date
        accrual_plan = self.accrual_plan_id
        carryover_date = False
        if carryover_time == 'year_start':
            carryover_date = date(date_from.year, 1, 1)
        elif carryover_time == 'allocation':
            carryover_date = date(date_from.year, self.date_from.month, self.date_from.day)
        else:
            month = int(accrual_plan.carryover_month)
            # 2020/2/31 will be changed to 2020/2/29
            day = min(monthrange(date_from.year, month)[1], int(accrual_plan.carryover_day))
            carryover_date = date(date_from.year, month, day)
        if date_from > carryover_date:
            carryover_date += relativedelta(years=1)
        return carryover_date

    def _add_days_to_allocation(self, current_level, current_level_maximum_leave, leaves_taken, period_start, period_end):
        days_to_add = self._process_accrual_plan_level(
            current_level, period_start, self.lastcall, period_end, self.nextcall)
        if current_level.cap_accrued_time_yearly:
            maximum_leave_yearly = current_level.maximum_leave_yearly\
                if current_level.added_value_type != 'hour'\
                else current_level.maximum_leave_yearly / self.employee_id._get_hours_per_day(self.date_from)
            yearly_remaining_amount = maximum_leave_yearly - self.yearly_accrued_amount
            days_to_add = min(days_to_add, yearly_remaining_amount)
        if current_level.cap_accrued_time:
            capped_total_balance = leaves_taken + current_level_maximum_leave
            days_to_add = min(days_to_add, capped_total_balance - self.number_of_days)
        self.number_of_days += days_to_add
        self.yearly_accrued_amount += days_to_add

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

    def _get_accrual_plan_level_work_entry_prorata(self, level, start_period, start_date, end_period, end_date):
        self.ensure_one()
        datetime_min_time = datetime.min.time()
        start_dt = datetime.combine(start_date, datetime_min_time)
        end_dt = datetime.combine(end_date, datetime_min_time)
        leaves_eligible = self.employee_id.sudo()._get_leave_days_data_batch(start_dt, end_dt,
            calendar=self.employee_id._get_calendars(start_dt)[self.employee_id.id],
            domain=[('time_type', '=', 'leave'), ('elligible_for_accrual_rate', '=', True)])[self.employee_id.id]['hours']
        worked = self.employee_id._get_work_days_data_batch(start_dt, end_dt,
            calendar=self.employee_id.resource_calendar_id)[self.employee_id.id]['hours']
        worked += leaves_eligible
        if start_period != start_date or end_period != end_date:
            start_dt = datetime.combine(start_period, datetime_min_time)
            end_dt = datetime.combine(end_period, datetime_min_time)
            leaves_eligible = self.employee_id.sudo()._get_leave_days_data_batch(start_dt, end_dt,
                calendar=self.employee_id._get_calendars(start_dt)[self.employee_id.id],
                domain=[('time_type', '=', 'leave'), ('elligible_for_accrual_rate', '=', True)])[self.employee_id.id]['hours']
            planned_worked = self.employee_id._get_work_days_data_batch(start_dt, end_dt,
                calendar=self.employee_id.resource_calendar_id)[self.employee_id.id]['hours']
            planned_worked += leaves_eligible
        else:
            planned_worked = worked
        left = self.employee_id.sudo()._get_leave_days_data_batch(start_dt, end_dt,
            calendar=self.employee_id._get_calendars(start_dt)[self.employee_id.id],
            domain=[('time_type', '=', 'leave'), ('elligible_for_accrual_rate', '=', False)])[self.employee_id.id]['hours']
        if level.frequency in level._get_hourly_frequencies():
            if level.accrual_plan_id.is_based_on_worked_time:
                work_entry_prorata = planned_worked
            else:
                work_entry_prorata = planned_worked + left
        else:
            work_entry_prorata = worked / (left + planned_worked) if (left + planned_worked) else 0
        return work_entry_prorata

    def _process_accrual_plan_level(self, level, start_period, start_date, end_period, end_date):
        """
        Returns the added days for that level
        """
        self.ensure_one()
        if level.frequency in level._get_hourly_frequencies() or level.accrual_plan_id.is_based_on_worked_time:
            work_entry_prorata = self._get_accrual_plan_level_work_entry_prorata(level, start_period, start_date, end_period, end_date)
            added_value = work_entry_prorata * level.added_value
        else:
            added_value = level.added_value
        # Convert time in hours to time in days in case the level is encoded in hours
        if level.added_value_type == 'hour':
            added_value = added_value / self.employee_id._get_hours_per_day(self.date_from)
        period_prorata = 1
        if (start_period != start_date or end_period != end_date) and not level.accrual_plan_id.is_based_on_worked_time:
            period_days = (end_period - start_period)
            call_days = (end_date - start_date)
            period_prorata = min(1, call_days / period_days) if period_days else 1
        return added_value * period_prorata

    def _process_accrual_plans(self, date_to=False, force_period=False, log=True):
        """
        This method is part of the cron's process.
        The goal of this method is to retroactively apply accrual plan levels and progress from nextcall to date_to or today.
        If force_period is set, the accrual will run until date_to in a prorated way (used for end of year accrual actions).
        """

        date_to = date_to or fields.Date.today()
        already_accrued = {allocation.id: allocation.already_accrued or (allocation.number_of_days != 0 and allocation.accrual_plan_id.accrued_gain_time == 'start') for allocation in self}
        first_allocation = _("""This allocation have already ran once, any modification won't be effective to the days allocated to the employee. If you need to change the configuration of the allocation, delete and create a new one.""")
        for allocation in self:
            expiration_date = False
            if allocation.allocation_type != 'accrual':
                continue
            level_ids = allocation.accrual_plan_id.level_ids.sorted('sequence')
            if not level_ids:
                continue
            # "cache" leaves taken, as it gets recomputed every time allocation.number_of_days is assigned to. Without this,
            # every loop will take 1+ second. It can be removed if computes don't chain in a way to always reassign accrual plan
            # even if the value doesn't change. This is the best performance atm.
            first_level = level_ids[0]
            first_level_start_date = allocation.date_from + get_timedelta(first_level.start_count, first_level.start_type)
            if allocation.holiday_status_id.request_unit in ["day", "half_day"]:
                leaves_taken = allocation.leaves_taken
            else:
                leaves_taken = allocation.leaves_taken / allocation.employee_id._get_hours_per_day(allocation.date_from)
            allocation.already_accrued = already_accrued[allocation.id]
            # first time the plan is run, initialize nextcall and take carryover / level transition into account
            if not allocation.nextcall:
                # Accrual plan is not configured properly or has not started
                if date_to < first_level_start_date:
                    continue
                allocation.lastcall = max(allocation.lastcall, first_level_start_date)
                allocation.actual_lastcall = allocation.lastcall
                allocation.nextcall = first_level._get_next_date(allocation.lastcall)
                # adjust nextcall for carryover
                carryover_date = allocation._get_carryover_date(allocation.nextcall)
                allocation.nextcall = min(carryover_date, allocation.nextcall)
                # adjust nextcall for level_transition
                if len(level_ids) > 1:
                    second_level_start_date = allocation.date_from + get_timedelta(level_ids[1].start_count, level_ids[1].start_type)
                    allocation.nextcall = min(second_level_start_date, allocation.nextcall)
                if log:
                    allocation._message_log(body=first_allocation)
            (current_level, current_level_idx) = (False, 0)
            current_level_maximum_leave = 0.0
            # all subsequent runs, at every loop:
            # get current level and normal period boundaries, then set nextcall, adjusted for level transition and carryover
            # add days, trimmed if there is a maximum_leave
            while allocation.nextcall <= date_to:
                (current_level, current_level_idx) = allocation._get_current_accrual_plan_level_id(allocation.nextcall)
                if not current_level:
                    break
                if current_level.cap_accrued_time:
                    if current_level.added_value_type == "day":
                        current_level_maximum_leave = current_level.maximum_leave
                    else:
                        current_level_maximum_leave = current_level.maximum_leave / allocation.employee_id._get_hours_per_day(allocation.date_from)
                nextcall = current_level._get_next_date(allocation.nextcall)
                # Since _get_previous_date returns the given date if it corresponds to a call date
                # this will always return lastcall except possibly on the first call
                # this is used to prorate the first number of days given to the employee
                period_start = current_level._get_previous_date(allocation.lastcall)
                period_end = current_level._get_next_date(allocation.lastcall)
                # There are 3 cases where nextcall could be closer than the normal period:
                # 1. Passing from one level to another, if mode is set to 'immediately'
                current_level_last_date = False
                if current_level_idx < (len(level_ids) - 1) and allocation.accrual_plan_id.transition_mode == 'immediately':
                    next_level = level_ids[current_level_idx + 1]
                    current_level_last_date = allocation.date_from + get_timedelta(next_level.start_count, next_level.start_type)
                    if allocation.nextcall != current_level_last_date:
                        nextcall = min(nextcall, current_level_last_date)
                # 2. On carry-over date
                carryover_date = allocation._get_carryover_date(allocation.nextcall)
                if allocation.nextcall < carryover_date < nextcall:
                    nextcall = min(nextcall, carryover_date)

                if current_level.accrual_validity:
                    # 3. On carried over days expiration date
                    expiration_date = allocation.carried_over_days_expiration_date
                    # - not expiration_date -> expiration_date needs to be initialized.
                    # - allocation.nextcall > expiration_date -> the expiration date has passed and the new one should be computed.
                    # - allocation.expiring_carryover_days == 0 -> If the carryover date of the accrual plan was changed or if a level
                    #   transition occurred, then the expiration date needs to be updated. However, if allocation.expiring_carryover_days != 0,
                    #   then this means that some days will expire on expiration_date and that expiration date should be respected and
                    #   Expiration date will be updated correctly when allocation.nextcall is greater than expiration_date.
                    if not expiration_date or allocation.nextcall > expiration_date or allocation.expiring_carryover_days == 0:
                        expiration_date = carryover_date + relativedelta(**{current_level.accrual_validity_type + 's': current_level.accrual_validity_count})
                        allocation.carried_over_days_expiration_date = expiration_date
                    if allocation.nextcall < expiration_date < nextcall:
                        nextcall = expiration_date
                    if allocation.nextcall == expiration_date:
                        # Given that allocation.number_of_days = employee time off balance + leaves_taken. So,
                        # the leaves_taken are included in allocation.number_of_days.
                        # Also, allocation.expiring_carryover_days includes the leaves_taken before the carryover date
                        # and allocation.leaves_taken includes all the leaves_taken before the carryover date + all the leaves_taken
                        # between the carryover date and the expiration_date. So, the number of expiring days will be
                        # allocation.expiring_carryover_days - allocation.leaves_taken or 0 if all the expiring days were used
                        # to take time off.
                        # This ensures that only the days that weren't used to take time off will expire.
                        expiring_days = max(0, allocation.expiring_carryover_days - allocation.leaves_taken)
                        allocation.number_of_days = max(0, allocation.number_of_days - expiring_days)
                        allocation.expiring_carryover_days = 0

                is_accrual_date = allocation.nextcall == period_end or allocation.nextcall == current_level_last_date
                if not allocation.already_accrued and is_accrual_date and allocation.accrual_plan_id.accrued_gain_time == 'start':
                    allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken, period_start, period_end)

                # if it's the carry-over date, adjust days using current level's carry-over policy
                if allocation.nextcall == carryover_date:
                    allocation.last_executed_carryover_date = carryover_date
                    if current_level.action_with_unused_accruals == 'lost' or current_level.carryover_options == 'limited':
                        allocated_days_left = allocation.number_of_days - leaves_taken
                        allocation_max_days = 0 # default if unused_accrual are lost
                        if current_level.carryover_options == 'limited':
                            if current_level.added_value_type == 'day':
                                postpone_max_days = current_level.postpone_max_days
                            else:
                                postpone_max_days = current_level.postpone_max_days / allocation.employee_id._get_hours_per_day(allocation.date_from)
                            allocation_max_days = min(postpone_max_days, allocated_days_left)
                        allocation.number_of_days = min(allocation.number_of_days, allocation_max_days) + leaves_taken
                    allocation.expiring_carryover_days = allocation.number_of_days

                if not allocation.already_accrued and is_accrual_date and allocation.accrual_plan_id.accrued_gain_time == 'end':
                    allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken, period_start, period_end)

                if allocation.nextcall == carryover_date:
                    allocation.yearly_accrued_amount = 0

                # 1. When accrued_gain_time == 'start', all the days are accrued on the start of the accrual period. For example, if the accrual period
                #    is from 01/01/2023 to 01/01/2024, then the days will be accrued on 01/01/2023. Given that the carryover date will be >= the start of the accrual period
                #    (01/01/2023 in the example) the carryover policy should apply to any day accrued during the period from 01/01/2023 to 01/01/2024.
                # 2.However, if a level transistion occurred, the carryover policy should apply to the days that were accrued during the carryover level only.
                #   Any days accrued after the carryover level should be excluded.
                #   So, if carryover date was 01/06/2023, it should be applied to any day accrued between 01/01/2023 and 01/01/2024. If a level transition
                #   occurred on 01/09/2023 for example, then the carryover should be applied to any day accrued between 01/01/2023 and 01/09/2023.
                # 3. The following if block will handle the carryover for days accrued after carryover_date until carryover_period_end. Carryover period end is
                #    adjusted if a level transition occurred. The carryover for days accrued before carryover_date is handled above.
                if allocation.accrual_plan_id.accrued_gain_time == 'start' and allocation.last_executed_carryover_date:
                    last_carryover_date = allocation.last_executed_carryover_date
                    carryover_level, carryover_level_idx = allocation._get_current_accrual_plan_level_id(last_carryover_date)
                    carryover_period_end = carryover_level._get_next_date(last_carryover_date)
                    # Adjust carryover_period_end based on level_transition.
                    if carryover_level_idx < (len(level_ids) - 1) and allocation.accrual_plan_id.transition_mode == 'immediately':
                        next_level = level_ids[carryover_level_idx + 1]
                        carryover_level_last_date = allocation.date_from + get_timedelta(next_level.start_count, next_level.start_type)
                        carryover_period_end = min(carryover_period_end, carryover_level_last_date)
                    # Handle the special case for hourly/daily accruals. Carryover_period_end should be equal to last_carryover_date
                    # because the carryover period is just 1 day.
                    if carryover_level.frequency in carryover_level._get_hourly_frequencies() + ['daily']:
                        carryover_period_end = last_carryover_date
                    # Carryover policy should be only applied to the days accrued on period_end.
                    # Days accrued on level transition date aren't subject to the carryover policy.
                    # That is why (allocation.nextcall == period_end) is used instead of (is_accrual_date)
                    accrued = not allocation.already_accrued and allocation.nextcall == period_end
                    # If the days were accrued on the carryover period, then apply the carryover policy
                    if accrued and last_carryover_date <= allocation.nextcall <= carryover_period_end:
                        if carryover_level.action_with_unused_accruals == 'lost' or carryover_level.carryover_options == 'limited':
                            allocation.last_executed_carryover_date = carryover_date
                            allocated_days_left = allocation.number_of_days - leaves_taken
                            postpone_max_days = current_level.postpone_max_days if current_level.added_value_type == 'day' \
                                else current_level.postpone_max_days / allocation.employee_id._get_hours_per_day(allocation.date_from)
                            allocated_days_left = allocation.number_of_days - leaves_taken
                            allocation_max_days = 0 # default if unused_accrual are lost
                            if current_level.carryover_options == 'limited':
                                postpone_max_days = current_level.postpone_max_days
                                allocation_max_days = min(postpone_max_days, allocated_days_left)
                            allocation.number_of_days = min(allocation.number_of_days, allocation_max_days) + leaves_taken

                if is_accrual_date:
                    allocation.lastcall = allocation.nextcall
                allocation.actual_lastcall = allocation.nextcall
                allocation.nextcall = nextcall
                allocation.already_accrued = False
                if force_period and allocation.nextcall > date_to:
                    allocation.nextcall = date_to
                    force_period = False

            # if plan.accrued_gain_time == 'start', process next period and set flag 'already_accrued', this will skip adding days
            # once, preventing double allocation.
            if allocation.accrual_plan_id.accrued_gain_time == 'start':
                # check that we are at the start of a period, not on a carry-over or level transition date
                level_start = {level._get_level_transition_date(allocation.date_from): level for level in allocation.accrual_plan_id.level_ids}
                current_level = level_start.get(allocation.actual_lastcall) or current_level or allocation.accrual_plan_id.level_ids[0]
                period_start = current_level._get_previous_date(allocation.actual_lastcall)
                if current_level.cap_accrued_time:
                    if current_level.added_value_type == "day":
                        current_level_maximum_leave = current_level.maximum_leave
                    else:
                        current_level_maximum_leave = current_level.maximum_leave / allocation.employee_id._get_hours_per_day(allocation.date_from)
                if allocation.actual_lastcall in {period_start, allocation.date_from} | set(level_start.keys())\
                        or (allocation.actual_lastcall - get_timedelta(current_level.accrual_validity_count, current_level.accrual_validity_type)
                            in {period_start, allocation.date_from} | set(level_start.keys())):
                    allocation._add_days_to_allocation(current_level, current_level_maximum_leave, leaves_taken, period_start, allocation.nextcall)
                    allocation.already_accrued = True

    @api.model
    def _update_accrual(self):
        """
        Method called by the cron task in order to increment the number_of_days when
        necessary.
        """
        today = datetime.combine(fields.Date.today(), time(0, 0, 0))
        allocations = self.search([
            ('allocation_type', '=', 'accrual'), ('state', '=', 'validate'),
            ('accrual_plan_id', '!=', False), ('employee_id', '!=', False),
            '|', ('date_to', '=', False), ('date_to', '>', fields.Datetime.now()),
            '|', ('nextcall', '=', False), ('nextcall', '<=', today)])
        allocations._process_accrual_plans()

    def _get_future_leaves_on(self, accrual_date):
        # As computing future accrual allocation days automatically updates the allocation,
        # We need to create a temporary copy of that allocation to return the difference in number of days
        # to see how much more days will be allocated from now until that date.
        self.ensure_one()
        if not accrual_date or accrual_date <= date.today():
            return 0

        if not (self.accrual_plan_id
                and self.state == 'validate'
                and self.allocation_type == 'accrual'
                and (not self.date_to or self.date_to > accrual_date)
                and (not self.nextcall or self.nextcall <= accrual_date)):
            return 0

        fake_allocation = self.env['hr.leave.allocation'].with_context(default_date_from=accrual_date).new(origin=self)
        fake_allocation.sudo().with_context(default_date_from=accrual_date)._process_accrual_plans(accrual_date, log=False)
        if self.holiday_status_id.request_unit in ['hour']:
            res = float_round(fake_allocation.number_of_hours_display - self.number_of_hours_display, precision_digits=2)
        else:
            res = round((fake_allocation.number_of_days - self.number_of_days), 2)
        fake_allocation.invalidate_recordset()
        return res

    def _get_next_states_by_state(self):
        self.ensure_one()
        state_result = {
            'confirm': set(),
            'validate1': set(),
            'validate': set(),
            'refuse': set(),
        }
        validation_type = self.validation_type

        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_time_off_manager = self.employee_id.leave_manager_id == self.env.user

        if is_officer:
            if validation_type == 'both':
                state_result['confirm'].add('validate1')
                state_result['refuse'].add('validate1')
            state_result['validate1'].update({'confirm', 'validate', 'refuse'})
            state_result['confirm'].update({'validate', 'refuse'})
            state_result['validate'].update({'confirm', 'refuse'})
            state_result['refuse'].update({'confirm', 'validate'})
        elif is_time_off_manager:
            if validation_type != 'hr':
                state_result['confirm'].add('refuse')
                state_result['validate'].add('refuse')
            if validation_type == 'both':
                state_result['confirm'].add('validate1')
                state_result['validate1'].add('refuse')
            elif validation_type == 'manager':
                state_result['confirm'].add('validate')
                state_result['refuse'].add('validate')

        if validation_type == 'no_validation':
            state_result['confirm'].add('validate')
        return state_result

    ####################################################
    # ORM Overrides methods
    ####################################################

    def onchange(self, values, field_names, fields_spec):
        # Try to force the leave_type display_name when creating new records
        # This is called right after pressing create and returns the display_name for
        # most fields in the view.
        if values and 'employee_id' in fields_spec and 'employee_id' not in self.env.context:
            employee_id = get_employee_from_context(values, self.env.context, self.env.user.employee_id.id)
            self = self.with_context(employee_id=employee_id)
        return super().onchange(values, field_names, fields_spec)

    @api.depends('employee_id', 'holiday_status_id', 'type_request_unit', 'number_of_days')
    def _compute_display_name(self):
        for allocation in self:
            allocation.display_name = _("Allocation of %(leave_type)s: %(amount).2f %(unit)s to %(target)s",
                leave_type=allocation.holiday_status_id.sudo().name,
                amount=allocation.number_of_hours_display if allocation.type_request_unit == 'hour' else allocation.number_of_days,
                unit=_('hours') if allocation.type_request_unit == 'hour' else _('days'),
                target=allocation.employee_id.name,
            )

    def _add_lastcalls(self):
        for allocation in self:
            if allocation.allocation_type != 'accrual':
                continue
            today = fields.Date.today()
            (current_level, current_level_idx) = allocation._get_current_accrual_plan_level_id(today)
            if not allocation.lastcall:
                if not current_level:
                    allocation.lastcall = today
                    allocation.actual_lastcall = allocation.lastcall
                    continue
                allocation.lastcall = max(
                    current_level._get_previous_date(today),
                    allocation.date_from + get_timedelta(current_level.start_count, current_level.start_type)
                )
                allocation.actual_lastcall = allocation.lastcall
            if current_level and not allocation.nextcall:
                accrual_plan = allocation.accrual_plan_id
                allocation.nextcall = current_level._get_next_date(allocation.lastcall)
                if current_level_idx < (len(accrual_plan.level_ids) - 1) and accrual_plan.transition_mode == 'immediately':
                    next_level = accrual_plan.level_ids[current_level_idx + 1]
                    next_level_start = allocation.date_from + get_timedelta(next_level.start_count, next_level.start_type)
                    allocation.nextcall = min(allocation.nextcall, next_level_start)
                # If the expiration date didn't pass (expiration date is in the future)
                expiration_date = allocation.carried_over_days_expiration_date
                if expiration_date and expiration_date > allocation.lastcall:
                    allocation.nextcall = min(allocation.nextcall, expiration_date)

    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe(partner_ids=employee.user_id.partner_id.ids)

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to avoid automatic logging of creation """
        for values in vals_list:
            if 'state' in values and values['state'] != 'confirm':
                raise UserError(_('Incorrect state for new allocation'))
            employee_id = values.get('employee_id', False)
            if not values.get('department_id'):
                values.update({'department_id': self.env['hr.employee'].sudo().browse(employee_id).department_id.id})
        allocations = super(HrLeaveAllocation, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        allocations._add_lastcalls()
        for allocation in allocations:
            partners_to_subscribe = set()
            if allocation.employee_id.user_id:
                partners_to_subscribe.add(allocation.employee_id.user_id.partner_id.id)
            if allocation.validation_type == 'hr':
                partners_to_subscribe.add(allocation.employee_id.sudo().parent_id.user_id.partner_id.id)
                partners_to_subscribe.add(allocation.employee_id.leave_manager_id.partner_id.id)
            allocation.message_subscribe(partner_ids=tuple(partners_to_subscribe))
            if not self.env.context.get('import_file'):
                allocation.activity_update()
            if allocation.validation_type == 'no_validation' and allocation.state == 'confirm':
                allocation.action_approve()
        return allocations

    def write(self, vals):
        values = vals
        employee_id = values.get('employee_id', False)
        if values.get('state'):
            self._check_approval_update(values['state'])

        self.add_follower(employee_id)

        if 'number_of_days_display' not in values and 'number_of_hours_display' not in values and 'state' not in values:
            res = super().write(values)
            if 'allocation_type' in values:
                self._add_lastcalls()
            return res

        previous_consumed_leaves = self.employee_id._get_consumed_leaves(leave_types=self.holiday_status_id)
        result = super().write(values)
        consumed_leaves = self.employee_id._get_consumed_leaves(leave_types=self.holiday_status_id)

        if 'allocation_type' in values:
            self._add_lastcalls()
        for allocation in self:
            current_excess = dict(consumed_leaves[1]).get(allocation.employee_id, {}) \
                .get(allocation.holiday_status_id, {}).get('excess_days', {})
            previous_excess = dict(previous_consumed_leaves[1]).get(allocation.employee_id, {}) \
                .get(allocation.holiday_status_id, {}).get('excess_days', {})
            total_current_excess = sum(leave_date['amount'] for leave_date in current_excess.values() if not leave_date['is_virtual'])
            total_previous_excess = sum(leave_date['amount'] for leave_date in previous_excess.values() if not leave_date['is_virtual'])

            if total_current_excess <= total_previous_excess:
                continue
            lt = allocation.holiday_status_id
            if lt.allows_negative and total_current_excess <= lt.max_allowed_negative:
                continue
            raise ValidationError(
                _('You cannot reduce the duration below the duration of leaves already taken by the employee.'))

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_correct_states(self):
        if self.env.context.get('allocation_skip_state_check'):
            return
        state_description_values = {elem[0]: elem[1] for elem in self._fields['state']._description_selection(self.env)}
        for allocation in self.filtered(lambda allocation: allocation.state not in ['confirm', 'refuse']):
            raise UserError(_('You cannot delete an allocation request which is in %s state.', state_description_values.get(allocation.state)))

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_leaves(self):
        if any(allocation.holiday_status_id.requires_allocation and allocation.leaves_taken > 0 for allocation in self):
            raise UserError(_('You cannot delete an allocation request which has some validated leaves.'))

    def copy(self, default=None):
        new_allocations = super().copy(default)
        new_allocations.state = 'confirm'
        return new_allocations

    def _get_redirect_suggested_company(self):
        return self.holiday_status_id.company_id

    ####################################################
    # Business methods
    ####################################################

    def action_approve(self):
        current_employee = self.env.user.employee_id
        allocation_to_approve = self.env['hr.leave.allocation']
        allocation_to_validate = self.env['hr.leave.allocation']
        for allocation in self:
            if allocation.can_validate:
                allocation_to_validate += allocation
            elif allocation.can_approve:
                allocation_to_approve += allocation
            else:
                raise UserError(_('Allocation must be "To Approve" in order to approve it.'))

        allocation_to_approve.write({'state': 'validate1', 'approver_id': current_employee.id})
        allocation_to_validate._action_validate()
        self.activity_update()
        return True

    def _action_validate(self):
        current_employee = self.env.user.employee_id

        allocation_both = self.filtered(lambda allocation: allocation.validation_type == 'both')
        allocation_first_approve = allocation_both.filtered(lambda allocation: not allocation.approver_id)
        allocation_first_approve.write(
            {'state': 'validate', 'approver_id': current_employee.id, 'second_approver_id': current_employee.id}
        )
        (allocation_both - allocation_first_approve).write(
            {'state': 'validate', 'second_approver_id': current_employee.id}
        )
        (self - allocation_both).write({'state': 'validate', 'approver_id': current_employee.id})

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(allocation.state not in ['confirm', 'validate', 'validate1'] for allocation in self):
            raise UserError(_('Allocation request must be confirmed, second approval or validated in order to refuse it.'))

        self.write({'state': 'refuse', 'approver_id': current_employee.id})
        self.activity_update()
        return True

    def _check_approval_update(self, state, raise_if_not_possible=True):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return True
        current_employee = self.env.user.employee_id
        is_administrator = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')
        for allocation in self:
            is_time_off_manager = allocation.employee_id.leave_manager_id == self.env.user
            error_message = ""
            dict_all_possible_state = allocation._get_next_states_by_state()
            if allocation.state == state:
                error_message = _('You can\'t do the same action twice.')
            elif allocation.employee_id == current_employee and \
                allocation.holiday_status_id.allocation_validation_type != 'no_validation' and not is_administrator:
                error_message = _('Only a time off Administrator can approve/refuse their own requests.')
            elif state not in dict_all_possible_state.get(allocation.state, {}):
                if state == 'confirm':
                    error_message = _('You can\'t reset an allocation. Cancel/delete this one and create an other')
                elif state == 'validate1':
                    if not is_time_off_manager:
                        error_message = _('Only a Time Off Officer/Manager can approve an allocation.')
                    else:
                        error_message = _('You can\'t approve a validated allocation.')
                elif state == 'validate':
                    if not is_time_off_manager:
                        error_message = _('Only a Time Off Officer/Manager can validate an allocation.')
                    elif allocation.state == "refuse":
                        error_message = _('You can\'t approve this refused allocation.')
                    else:
                        error_message = _('You can only validate an allocation with validation by Time Off Manager.')
                elif state == "refuse":
                    if not is_time_off_manager:
                        error_message = _('Only a Time Off Officer/Manager can refuse an allocation.')
                    else:
                        error_message = _('You can\'t refuse an allocation with validation by Time Off Officer.')
                else:
                    try:
                        allocation.check_access('write')
                    except UserError as e:
                        if raise_if_not_possible:
                            raise UserError(e)
                        return False
                    else:
                        continue
            if error_message:
                if raise_if_not_possible:
                    raise UserError(error_message)
                return False
        return True

    @api.onchange('allocation_type')
    def _onchange_allocation_type(self):
        if self.allocation_type == 'accrual':
            self.number_of_days = 0.0
        elif not self.number_of_days_display:
            self.number_of_days = 1.0

    # Allows user to simulate how many days an accrual plan would give from a certain start date.
    # it uses the actual computation function but resets values of lastcall, nextcall and nbr of days
    # before every run, as if it was run from date_from, after an optional change in the allocation value
    # the user can simply confirm and validate the allocation. The record is in correct state for the next
    # call of the cron job.
    @api.onchange('date_from', 'accrual_plan_id', 'date_to', 'employee_id')
    def _onchange_date_from(self):
        if not self.date_from or self.allocation_type != 'accrual' or self.state == 'validate' or not self.accrual_plan_id\
           or not self.employee_id:
            return
        self.lastcall = self.date_from
        self.nextcall = False
        self.number_of_days_display = 0.0
        self.number_of_hours_display = 0.0
        self.number_of_days = 0.0
        self.already_accrued = False
        self.carried_over_days_expiration_date = False
        self.expiring_carryover_days = 0
        date_to = min(self.date_to, date.today()) if self.date_to else False
        self._process_accrual_plans(date_to)

    # ------------------------------------------------------------
    # Activity methods
    # ------------------------------------------------------------

    def _get_responsible_for_approval(self):
        self.ensure_one()
        responsible = self.env['res.users']

        if self.validation_type == 'manager' or (self.validation_type == 'both' and self.state == 'confirm'):
            if self.employee_id.leave_manager_id:
                responsible = self.employee_id.leave_manager_id
            elif self.employee_id.parent_id.user_id:
                responsible = self.employee_id.parent_id.user_id
        elif self.validation_type == 'hr' or (self.validation_type == 'both' and self.state == 'validate1'):
            if self.holiday_status_id.responsible_ids:
                responsible = self.holiday_status_id.responsible_ids

        return responsible

    def activity_update(self):
        to_clean, to_do, to_second_do = self.env['hr.leave.allocation'], self.env['hr.leave.allocation'], self.env['hr.leave.allocation']
        activity_vals = []
        model_id = self.env['ir.model']._get_id('hr.leave.allocation')
        confirm_activity = self.env.ref('hr_holidays.mail_act_leave_allocation_approval')
        approval_activity = self.env.ref('hr_holidays.mail_act_leave_allocation_second_approval')
        for allocation in self:
            if allocation.state in ['confirm', 'validate1']:
                if allocation.holiday_status_id.leave_validation_type != 'no_validation':
                    if allocation.state == 'confirm':
                        activity_type = confirm_activity
                        note = _(
                            'New Allocation Request created by %(user)s: %(count)s Days of %(allocation_type)s',
                            user=allocation.create_uid.name,
                            count=float_round(allocation.number_of_days, precision_digits=2),
                            allocation_type=allocation.holiday_status_id.name,
                        )
                    else:
                        activity_type = approval_activity
                        note = _(
                            'Second approval request for %(allocation_type)s',
                            allocation_type=allocation.holiday_status_id.name,
                        )
                        to_second_do |= allocation
                    user_ids = allocation.sudo()._get_responsible_for_approval().ids
                    for user_id in user_ids:
                        activity_vals.append({
                            'activity_type_id': activity_type.id,
                            'automated': True,
                            'note': note,
                            'user_id': user_id,
                            'res_id': allocation.id,
                            'res_model_id': model_id,
                        })
            elif allocation.state == 'validate':
                to_do |= allocation

            elif allocation.state == 'refuse':
                to_clean |= allocation

        if to_clean:
            to_clean.activity_unlink(['hr_holidays.mail_act_leave_allocation_approval'])
        if to_do:
            to_do.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval', 'hr_holidays.mail_act_leave_allocation_second_approval'])
        if to_second_do:
            to_second_do.activity_feedback(['hr_holidays.mail_act_leave_allocation_approval'])

        if activity_vals:
            self.env['mail.activity'].create(activity_vals)

    ####################################################
    # Messaging methods
    ####################################################

    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            allocation_notif_subtype_id = self.holiday_status_id.allocation_notif_subtype_id
            return allocation_notif_subtype_id or self.env.ref('hr_holidays.mt_leave_allocation')
        return super()._track_subtype(init_values)

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        # due to record rule can not allow to add follower and mention on validated leave so subscribe through sudo
        if any(state in ['validate'] for state in self.mapped('state')):
            self.check_access('read')
            return super(HrLeaveAllocation, self.sudo()).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)
        return super().message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)
