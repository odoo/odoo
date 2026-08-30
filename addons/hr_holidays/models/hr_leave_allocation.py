from calendar import monthrange
from datetime import date, datetime, time

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_round
from odoo.tools import format_date
from odoo.tools.date_utils import get_timedelta

_debug = DebugLog(__name__)


class HrLeaveAllocation(models.Model):
    _name = "hr.leave.allocation"
    _description = "Time Off Allocation"
    _order = "create_date desc"
    _inherit = ["mixin.hr.leave.approval", "mixin.mail.thread", "mixin.mail.activity"]
    _mail_post_access = "read"

    def _default_holiday_status_id(self):
        if self.env.user.has_group("hr_holidays.group_hr_holidays_user"):
            domain = [
                ("has_valid_allocation", "=", True),
                ("requires_allocation", "=", True),
            ]
        else:
            domain = [
                ("has_valid_allocation", "=", True),
                ("requires_allocation", "=", True),
                ("employee_requests", "=", True),
            ]
        return self.env["hr.leave.type"].search(domain, limit=1)

    def _domain_holiday_status_id(self):
        domain = [
            ("company_id", "in", self.env.companies.ids + [False]),
            ("requires_allocation", "=", True),
        ]
        if self.env.user.has_group("hr_holidays.group_hr_holidays_user"):
            return domain
        return Domain.AND([domain, [("employee_requests", "=", True)]])

    def _domain_employee_id(self):
        domain = [("company_id", "in", self.env.companies.ids)]
        if not self.env.user.has_group("hr_holidays.group_hr_holidays_user"):
            domain += [("leave_manager_id", "=", self.env.user.id)]
        return domain

    name = fields.Char(
        string="Description",
        compute="_compute_name",
        compute_sudo=False,
        store=True,
        readonly=False,
    )
    is_name_custom = fields.Boolean(
        string="Name Set By Hand",
        export_string_translation=False,
        default=False,
        readonly=True,
        help="Set when someone writes a description of their own, so that the "
        "generated one stops overwriting it.",
    )
    name_validity = fields.Char(
        string="Description with validity",
        compute="_compute_name_validity",
    )
    state = fields.Selection(
        selection=[
            ("confirm", "To Approve"),
            ("refuse", "Refused"),
            ("validate1", "Second Approval"),
            ("validate", "Approved"),
        ],
        string="Status",
        default="confirm",
        copy=False,
        readonly=True,
        tracking=True,
        help="The status is 'To Approve', when an allocation request is created."
        "\nThe status is 'Refused', when an allocation request is refused by manager."
        "\nThe status is 'Approved', when an allocation request is approved by manager.",
    )
    date_from = fields.Date(
        string="Start Date",
        default=fields.Date.context_today,
        index=True,
        copy=False,
        required=True,
        tracking=True,
    )
    date_to = fields.Date(
        string="End Date",
        copy=False,
        tracking=True,
    )
    holiday_status_id = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Time Off Type",
        compute="_compute_holiday_status_id",
        default=_default_holiday_status_id,
        store=True,
        readonly=False,
        required=True,
        domain=_domain_holiday_status_id,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        default=lambda self: self.env.user.employee_id,
        index=True,
        required=True,
        domain=_domain_employee_id,
        ondelete="restrict",
        tracking=True,
    )
    employee_company_id = fields.Many2one(
        related="employee_id.company_id",
        readonly=True,
    )
    active_employee = fields.Boolean(
        related="employee_id.active",
        string="Active Employee",
        readonly=True,
    )
    manager_id = fields.Many2one(
        comodel_name="hr.employee",
        compute="_compute_manager_id",
        store=True,
    )
    notes = fields.Text(
        string="Reasons",
        readonly=False,
    )
    number_of_days = fields.Float(
        string="Number of Days",
        compute="_compute_number_of_days",
        default=1,
        store=True,
        readonly=False,
        tracking=True,
        help="Duration in days. Reference field to use when necessary.",
    )
    number_of_days_display = fields.Float(
        string="Duration (days)",
        compute="_compute_number_of_days_display",
        help="For an Accrual Allocation, this field contains the theorical amount of time given to the employee, due to a previous start date, on the first run of the plan. This can be manually edited.",
    )
    number_of_hours_display = fields.Float(
        string="Duration (hours)",
        compute="_compute_number_of_hours_display",
        store=True,
        default_export_compatible=True,
        help="For an Accrual Allocation, this field contains the theorical amount of time given to the employee, due to a previous start date, on the first run of the plan. This can be manually edited.",
    )
    duration_display = fields.Char(
        string="Allocated (Days/Hours)",
        compute="_compute_duration_display",
        help="Field allowing to see the allocation duration in days or hours depending on the type_request_unit",
    )
    last_executed_carryover_date = fields.Date(export_string_translation=False)
    approver_id = fields.Many2one(
        comodel_name="hr.employee",
        string="First Approval",
        copy=False,
        readonly=True,
        help="This area is automatically filled by the user who validates the allocation",
    )
    second_approver_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Second Approval",
        copy=False,
        readonly=True,
        help="This area is automatically filled by the user who validates the allocation with second level (If time off type need second validation)",
    )
    validation_type = fields.Selection(
        related="holiday_status_id.allocation_validation_type",
        string="Validation Type",
        readonly=True,
    )
    type_request_unit = fields.Selection(
        selection=[
            ("hour", "Hours"),
            ("half_day", "Half-Day"),
            ("day", "Day"),
        ],
        compute="_compute_type_request_unit",
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        compute="_compute_department_id",
        store=True,
        readonly=False,
    )
    lastcall = fields.Date(
        string="Date of the last accrual allocation",
        readonly=True,
    )
    actual_lastcall = fields.Date(export_string_translation=False)
    nextcall = fields.Date(
        string="Date of the next accrual allocation",
        default=False,
        readonly=True,
    )
    already_accrued = fields.Boolean()
    yearly_accrued_amount = fields.Float(export_string_translation=False)
    allocation_type = fields.Selection(
        selection=[
            ("regular", "Regular Allocation"),
            ("accrual", "Accrual Allocation"),
        ],
        default="regular",
        readonly=True,
        required=True,
    )
    is_officer = fields.Boolean(compute="_compute_is_officer")
    accrual_plan_id = fields.Many2one(
        comodel_name="hr.leave.accrual.plan",
        compute="_compute_accrual_plan_id",
        inverse="_inverse_accrual_plan_id",
        store=True,
        index="btree_not_null",
        readonly=False,
        domain="['|', ('time_off_type_id', '=', False), ('time_off_type_id', '=', holiday_status_id)]",
        tracking=True,
    )
    max_leaves = fields.Float(compute="_compute_leaves")
    leaves_taken = fields.Float(
        string="Time off Taken",
        compute="_compute_leaves",
    )
    virtual_remaining_leaves = fields.Float(
        string="Available Time Off",
        compute="_compute_leaves",
    )
    expiring_carryover_days = fields.Float(
        string="The number of carried over days that will expire on carried_over_days_expiration_date"
    )
    carried_over_days_expiration_date = fields.Date(
        string="Carried over days expiration date"
    )
    _duration_check = models.Constraint(
        "CHECK( ( number_of_days > 0 AND allocation_type='regular') or (allocation_type != 'regular'))",
        "The duration must be greater than 0.",
    )

    @api.constrains("date_from", "date_to")
    def _check_date_from_date_to(self):
        if any(
            allocation.date_to and allocation.date_from > allocation.date_to
            for allocation in self
        ):
            raise UserError(
                _(
                    "The Start Date of the Validity Period must be anterior to the End Date."
                )
            )

    @api.depends_context("uid")
    def _compute_is_officer(self):
        self.is_officer = self.env.user.has_group("hr_holidays.group_hr_holidays_user")

    def _get_title(self):
        self.check_singleton()
        if not self.holiday_status_id:
            return _("Allocation Request")
        if self.type_request_unit == "hour":
            return _(
                "%(name)s (%(duration)s hour(s))",
                name=self.holiday_status_id.name,
                duration=self.number_of_days
                * self.employee_id._get_hours_per_day(self.date_from),
            )
        return _(
            "%(name)s (%(duration)s day(s))",
            name=self.holiday_status_id.name,
            duration=float_round(self.number_of_days, precision_digits=2),
        )

    def _mark_custom_names(self):
        """Record which allocations carry a description nobody generated.

        Called after the values are in, so ``_get_title()`` is the title the
        record would have had; anything else is somebody's own wording and
        ``_compute_name`` must leave it alone from here on. The flag is stored
        because the alternative -- deciding it again at each write -- cannot
        tell a rename from a leave type that changed under an unchanged name.
        """
        for allocation in self:
            is_custom = bool(allocation.name) and allocation.name != (
                allocation._get_title()
            )
            if allocation.is_name_custom != is_custom:
                allocation.is_name_custom = is_custom
                _debug.lifecycle(
                    "allocation_description",
                    allocation=allocation,
                    custom=is_custom,
                    name=allocation.name,
                )

    @api.depends("holiday_status_id", "number_of_days")
    def _compute_name(self):
        for allocation in self:
            if not allocation.is_name_custom:
                allocation.name = allocation._get_title()

    @api.depends("name", "date_from", "date_to")
    @api.depends_context("lang")
    def _compute_name_validity(self):
        for allocation in self:
            allocation_date_from = fields.Datetime.to_datetime(
                allocation.date_from or fields.Date.context_today(allocation)
            )
            allocation_date_to = fields.Datetime.to_datetime(allocation.date_to)

            if allocation.date_to:
                name_validity = self.env._(
                    "%(allocation_name)s (from %(date_from)s to %(date_to)s)",
                    allocation_name=allocation.name,
                    date_from=format_date(
                        allocation.env,
                        fields.Date.context_today(allocation, allocation_date_from),
                    ),
                    date_to=format_date(
                        allocation.env,
                        fields.Date.context_today(allocation, allocation_date_to),
                    ),
                )
            else:
                name_validity = self.env._(
                    "%(allocation_name)s (from %(date_from)s to No Limit)",
                    allocation_name=allocation.name,
                    date_from=format_date(
                        allocation.env,
                        fields.Date.context_today(allocation, allocation_date_from),
                    ),
                )
            allocation.name_validity = name_validity

    @api.depends("employee_id", "holiday_status_id")
    @api.depends_context("default_date_from")
    def _compute_leaves(self):
        date_from = (
            fields.Date.from_string(self.env.context["default_date_from"])
            if "default_date_from" in self.env.context
            else fields.Date.context_today(self)
        )
        employee_days_per_allocation = self.employee_id._get_consumed_leaves(
            self.holiday_status_id, date_from
        )[0]
        for allocation in self:
            origin = allocation._origin
            virtual_leave = employee_days_per_allocation[origin.employee_id][
                origin.holiday_status_id
            ][origin]
            allocation.max_leaves = virtual_leave["max_leaves"]
            allocation.leaves_taken = virtual_leave["leaves_taken"]
            allocation.virtual_remaining_leaves = virtual_leave[
                "virtual_remaining_leaves"
            ]

    @api.depends("number_of_days")
    def _compute_number_of_days_display(self):
        for allocation in self:
            allocation.number_of_days_display = allocation.number_of_days

    @api.depends("number_of_days", "employee_id")
    def _compute_number_of_hours_display(self):
        for allocation in self:
            if not allocation.employee_id:
                continue
            allocation.number_of_hours_display = (
                allocation.number_of_days
                * allocation.employee_id._get_hours_per_day(allocation.date_from)
            )

    @api.depends("number_of_hours_display", "number_of_days_display")
    def _compute_duration_display(self):
        for allocation in self:
            allocation.duration_display = "%g %s" % (
                (
                    float_round(allocation.number_of_hours_display, precision_digits=2)
                    if allocation.type_request_unit == "hour"
                    else float_round(
                        allocation.number_of_days_display, precision_digits=2
                    )
                ),
                _("hours") if allocation.type_request_unit == "hour" else _("days"),
            )

    @api.depends("employee_id")
    def _compute_department_id(self):
        for allocation in self:
            allocation.department_id = allocation.employee_id.department_id

    @api.depends("employee_id")
    def _compute_manager_id(self):
        for allocation in self:
            allocation.manager_id = (
                allocation.employee_id and allocation.employee_id.parent_id
            )

    @api.depends("accrual_plan_id")
    def _compute_holiday_status_id(self):
        default_holiday_status_id = None
        for allocation in self:
            if not allocation.holiday_status_id:
                if allocation.accrual_plan_id:
                    allocation.holiday_status_id = (
                        allocation.accrual_plan_id.time_off_type_id
                    )
                else:
                    if not default_holiday_status_id:
                        default_holiday_status_id = self._default_holiday_status_id()
                    allocation.holiday_status_id = default_holiday_status_id

    @api.depends(
        "holiday_status_id",
        "number_of_hours_display",
        "number_of_days_display",
        "type_request_unit",
        "employee_id",
    )
    def _compute_number_of_days(self):
        for allocation in self:
            allocation_unit = allocation.type_request_unit
            if allocation_unit != "hour":
                allocation.number_of_days = allocation.number_of_days_display
            elif allocation.employee_id:
                allocation.number_of_days = (
                    allocation.number_of_hours_display
                    / allocation.employee_id._get_hours_per_day(allocation.date_from)
                )

    @api.depends("holiday_status_id", "allocation_type")
    def _compute_accrual_plan_id(self):
        accrual_allocations = self.filtered(
            lambda alloc: (
                alloc.allocation_type == "accrual"
                and not alloc.accrual_plan_id
                and alloc.holiday_status_id
            )
        )
        accruals_read_group = self.env["hr.leave.accrual.plan"]._read_group(
            [("time_off_type_id", "in", accrual_allocations.holiday_status_id.ids)],
            ["time_off_type_id"],
            ["id:array_agg"],
        )
        accruals_dict = {
            time_off_type.id: ids for time_off_type, ids in accruals_read_group
        }
        for allocation in self:
            if (
                allocation.allocation_type == "regular" and allocation.accrual_plan_id
            ) or allocation.accrual_plan_id.time_off_type_id.id not in (
                False,
                allocation.holiday_status_id.id,
            ):
                allocation.accrual_plan_id = False
            if (
                allocation.allocation_type == "accrual"
                and not allocation.accrual_plan_id
            ):
                if allocation.holiday_status_id:
                    allocation.accrual_plan_id = accruals_dict.get(
                        allocation.holiday_status_id.id, [False]
                    )[0]

    def _inverse_accrual_plan_id(self):
        for allocation in self:
            allocation.allocation_type = (
                "accrual" if allocation.accrual_plan_id else "regular"
            )

    def _get_request_unit(self):
        self.check_singleton()
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
        self.check_singleton()
        carryover_time = self.accrual_plan_id.carryover_date
        accrual_plan = self.accrual_plan_id
        carryover_date = False
        if carryover_time == "year_start":
            carryover_date = date(date_from.year, 1, 1)
        elif carryover_time == "allocation":
            day = min(
                monthrange(date_from.year, self.date_from.month)[1],
                self.date_from.day,
            )
            carryover_date = date(date_from.year, self.date_from.month, day)
        else:
            month = int(accrual_plan.carryover_month)
            day = min(
                monthrange(date_from.year, month)[1], int(accrual_plan.carryover_day)
            )
            carryover_date = date(date_from.year, month, day)
        if date_from > carryover_date:
            carryover_date += relativedelta(years=1)
        return carryover_date

    def _level_amount_in_days(self, level, amount):
        self.check_singleton()
        if level.added_value_type == "day":
            return amount
        return amount / self.employee_id._get_hours_per_day(self.date_from)

    def _apply_carryover_limit(self, level, leaves_taken):
        self.check_singleton()
        if (
            level.action_with_unused_accruals != "lost"
            and level.carryover_options != "limited"
        ):
            return False
        allocation_max_days = 0
        if level.carryover_options == "limited":
            allocation_max_days = min(
                self._level_amount_in_days(level, level.postpone_max_days),
                self.number_of_days - leaves_taken,
            )
        self.number_of_days = (
            min(self.number_of_days, allocation_max_days) + leaves_taken
        )
        return True

    def _add_days_to_allocation(
        self,
        current_level,
        current_level_maximum_leave,
        leaves_taken,
        period_start,
        period_end,
    ):
        days_to_add = self._process_accrual_plan_level(
            current_level, period_start, self.lastcall, period_end, self.nextcall
        )
        if current_level.cap_accrued_time_yearly:
            maximum_leave_yearly = self._level_amount_in_days(
                current_level, current_level.maximum_leave_yearly
            )
            yearly_remaining_amount = maximum_leave_yearly - self.yearly_accrued_amount
            days_to_add = min(days_to_add, yearly_remaining_amount)
        if current_level.cap_accrued_time:
            capped_total_balance = leaves_taken + current_level_maximum_leave
            days_to_add = min(days_to_add, capped_total_balance - self.number_of_days)
        self.number_of_days += days_to_add
        self.yearly_accrued_amount += days_to_add

    def _get_current_accrual_plan_level_id(self, date, level_ids=False):
        self.check_singleton()
        if not self.accrual_plan_id.level_ids:
            return (False, False)
        if not level_ids:
            level_ids = self.accrual_plan_id.level_ids.sorted("sequence")
        current_level = False
        current_level_idx = -1
        for idx, level in enumerate(level_ids):
            if date > self.date_from + get_timedelta(
                level.start_count, level.start_type
            ):
                current_level = level
                current_level_idx = idx
        if (
            current_level_idx <= 0
            or self.accrual_plan_id.transition_mode == "immediately"
        ):
            return (current_level, current_level_idx)
        level_start_date = self.date_from + get_timedelta(
            current_level.start_count, current_level.start_type
        )
        previous_level = level_ids[current_level_idx - 1]
        if current_level._get_next_anchor(
            level_start_date
        ) < previous_level._get_next_anchor(level_start_date):
            return (previous_level, current_level_idx - 1)
        return (current_level, current_level_idx)

    def _accrual_leave_hours(self, start, end, eligible_for_accrual_rate):
        self.check_singleton()
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.min.time())
        return self.employee_id.sudo()._get_leave_days_data_batch(
            start_dt,
            end_dt,
            calendar=self.employee_id._get_calendars(start_dt)[self.employee_id.id],
            domain=[
                ("time_type_id.is_work", "=", False),
                ("eligible_for_accrual_rate", "=", eligible_for_accrual_rate),
            ],
        )[self.employee_id.id]["hours"]

    def _accrual_worked_hours(self, start, end):
        self.check_singleton()
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.min.time())
        return self.employee_id._get_work_days_data_batch(
            start_dt, end_dt, calendar=self.employee_id.resource_calendar_id
        )[self.employee_id.id]["hours"]

    def _get_accrual_plan_level_work_entry_prorata(
        self, level, start_period, start_date, end_period, end_date
    ):
        self.check_singleton()
        worked = self._accrual_worked_hours(
            start_date, end_date
        ) + self._accrual_leave_hours(start_date, end_date, True)
        if (start_period, end_period) != (start_date, end_date):
            planned_start, planned_end = start_period, end_period
            planned_worked = self._accrual_worked_hours(
                planned_start, planned_end
            ) + self._accrual_leave_hours(planned_start, planned_end, True)
        else:
            planned_start, planned_end = start_date, end_date
            planned_worked = worked
        left = self._accrual_leave_hours(planned_start, planned_end, False)
        if level.accrual_basis in level._get_hourly_bases():
            if level.accrual_plan_id.is_based_on_worked_time:
                work_entry_prorata = planned_worked
            else:
                work_entry_prorata = planned_worked + left
        else:
            work_entry_prorata = (
                worked / (left + planned_worked) if (left + planned_worked) else 0
            )
        return work_entry_prorata

    def _process_accrual_plan_level(
        self, level, start_period, start_date, end_period, end_date
    ):
        self.check_singleton()
        if (
            level.accrual_basis in level._get_hourly_bases()
            or level.accrual_plan_id.is_based_on_worked_time
        ):
            work_entry_prorata = self._get_accrual_plan_level_work_entry_prorata(
                level, start_period, start_date, end_period, end_date
            )
            added_value = work_entry_prorata * level.added_value
        else:
            added_value = level.added_value
        added_value = self._level_amount_in_days(level, added_value)
        period_prorata = 1
        if (
            start_period != start_date or end_period != end_date
        ) and not level.accrual_plan_id.is_based_on_worked_time:
            period_days = end_period - start_period
            call_days = end_date - start_date
            period_prorata = min(1, call_days / period_days) if period_days else 1
        return added_value * period_prorata

    def _update_initial_accrual_schedule(self, level_ids, date_to, log):
        """Place the first accrual call of an allocation that has never run.

        Returns False when the plan has not started by `date_to`, which is the
        caller's signal that there is nothing to accrue yet.
        """
        self.check_singleton()
        first_level = level_ids[0]
        first_level_start_date = self.date_from + get_timedelta(
            first_level.start_count, first_level.start_type
        )
        if date_to < first_level_start_date:
            return False
        self.lastcall = max(self.lastcall, first_level_start_date)
        self.actual_lastcall = self.lastcall
        self.nextcall = first_level._get_next_anchor(self.lastcall)
        carryover_date = self._get_carryover_date(self.nextcall)
        self.nextcall = min(carryover_date, self.nextcall)
        if len(level_ids) > 1:
            second_level_start_date = self.date_from + get_timedelta(
                level_ids[1].start_count, level_ids[1].start_type
            )
            self.nextcall = min(second_level_start_date, self.nextcall)
        if log:
            self._message_log(
                body=_(
                    """This allocation have already ran once, any modification won't be effective to the days allocated to the employee. If you need to change the configuration of the allocation, delete and create a new one."""
                )
            )
        return True

    def _accrual_step_bounds(self, current_level, current_level_idx, level_ids):
        """Where the step the allocation is standing on begins and ends.

        `nextcall` is where the cursor moves to, and is pulled back to the next
        level's start date when the plan changes level the moment it is due
        rather than at the end of the period.
        """
        self.check_singleton()
        nextcall = current_level._get_next_anchor(self.nextcall)
        period_start = current_level._get_previous_anchor(self.lastcall)
        period_end = current_level._get_next_anchor(self.lastcall)
        current_level_last_date = False
        if (
            current_level_idx < (len(level_ids) - 1)
            and self.accrual_plan_id.transition_mode == "immediately"
        ):
            next_level = level_ids[current_level_idx + 1]
            current_level_last_date = self.date_from + get_timedelta(
                next_level.start_count, next_level.start_type
            )
            if self.nextcall != current_level_last_date:
                nextcall = min(nextcall, current_level_last_date)
        return nextcall, period_start, period_end, current_level_last_date

    def _expire_carried_over_days(self, current_level, carryover_date, nextcall):
        """Drop the carried-over days whose validity has run out, and stop the
        cursor on the expiry date if it falls inside the step.

        Returns the step's end, which the expiry may have brought forward.
        """
        self.check_singleton()
        expiration_date = self.carried_over_days_expiration_date
        if (
            not expiration_date
            or self.nextcall > expiration_date
            or self.expiring_carryover_days == 0
        ):
            expiration_date = carryover_date + relativedelta(
                **{
                    current_level.accrual_validity_type
                    + "s": current_level.accrual_validity_count
                }
            )
            self.carried_over_days_expiration_date = expiration_date
        if self.nextcall < expiration_date < nextcall:
            nextcall = expiration_date
        if self.nextcall == expiration_date:
            expiring_days = max(0, self.expiring_carryover_days - self.leaves_taken)
            self.number_of_days = max(0, self.number_of_days - expiring_days)
            self.expiring_carryover_days = 0
        return nextcall

    def _run_accrual_steps(self, level_ids, date_to, force_period, leaves_taken):
        """Walk the plan forward one accrual period at a time, up to `date_to`.

        Returns the level it stopped on, that level's cap in days and what is
        left of `force_period` -- which the caller threads through its whole
        recordset, because the first allocation to consume it spends it for all
        of them.
        """
        self.check_singleton()
        (current_level, current_level_idx) = (False, 0)
        current_level_maximum_leave = 0.0
        cap_days_by_level = {}
        while self._get_accrual_step_date() <= date_to:
            (current_level, current_level_idx) = (
                self._get_current_accrual_plan_level_id(self.nextcall)
            )
            if not current_level:
                break
            if current_level.cap_accrued_time:
                if current_level.id not in cap_days_by_level:
                    cap_days_by_level[current_level.id] = self._level_amount_in_days(
                        current_level, current_level.maximum_leave
                    )
                current_level_maximum_leave = cap_days_by_level[current_level.id]
            nextcall, period_start, period_end, current_level_last_date = (
                self._accrual_step_bounds(current_level, current_level_idx, level_ids)
            )
            carryover_date = self._get_carryover_date(self.nextcall)
            if self.nextcall < carryover_date < nextcall:
                nextcall = min(nextcall, carryover_date)

            is_accrual_date = self.nextcall in (
                period_end,
                current_level_last_date,
            )
            # A last-day period is credited on its last day, a day before its
            # boundary, so the credit precedes whatever else happens at the
            # boundary: a carryover, an expiry, the next level.
            if (
                self.accrual_plan_id.accrued_gain_time == "end"
                and self.nextcall == period_end
                and current_level._get_anchor_day(period_end) < period_end
                and not self.already_accrued
            ):
                self._add_days_to_allocation(
                    current_level,
                    current_level_maximum_leave,
                    leaves_taken,
                    period_start,
                    period_end,
                )
                self.already_accrued = True
            if self.nextcall > date_to:
                break

            if current_level.accrual_validity:
                nextcall = self._expire_carried_over_days(
                    current_level, carryover_date, nextcall
                )

            if (
                not self.already_accrued
                and is_accrual_date
                and self.accrual_plan_id.accrued_gain_time == "start"
            ):
                self._add_days_to_allocation(
                    current_level,
                    current_level_maximum_leave,
                    leaves_taken,
                    period_start,
                    period_end,
                )

            if self.nextcall == carryover_date:
                self.last_executed_carryover_date = carryover_date
                self._apply_carryover_limit(current_level, leaves_taken)
                self.expiring_carryover_days = self.number_of_days

            if (
                not self.already_accrued
                and is_accrual_date
                and self.accrual_plan_id.accrued_gain_time == "end"
            ):
                self._add_days_to_allocation(
                    current_level,
                    current_level_maximum_leave,
                    leaves_taken,
                    period_start,
                    period_end,
                )

            if self.nextcall == carryover_date:
                self.yearly_accrued_amount = 0

            if (
                self.accrual_plan_id.accrued_gain_time == "start"
                and self.last_executed_carryover_date
            ):
                last_carryover_date = self.last_executed_carryover_date
                carryover_level, carryover_level_idx = (
                    self._get_current_accrual_plan_level_id(last_carryover_date)
                )
                carryover_period_end = carryover_level._get_next_anchor(
                    last_carryover_date
                )
                if (
                    carryover_level_idx < (len(level_ids) - 1)
                    and self.accrual_plan_id.transition_mode == "immediately"
                ):
                    next_level = level_ids[carryover_level_idx + 1]
                    carryover_level_last_date = self.date_from + get_timedelta(
                        next_level.start_count, next_level.start_type
                    )
                    carryover_period_end = min(
                        carryover_period_end, carryover_level_last_date
                    )
                if carryover_level.repeat_unit == "day":
                    carryover_period_end = last_carryover_date
                accrued = not self.already_accrued and self.nextcall == period_end
                if (
                    accrued
                    and last_carryover_date <= self.nextcall <= carryover_period_end
                ):
                    if self._apply_carryover_limit(carryover_level, leaves_taken):
                        self.last_executed_carryover_date = carryover_date

            if is_accrual_date:
                self.lastcall = self.nextcall
            self.actual_lastcall = self.nextcall
            self.nextcall = nextcall
            self.already_accrued = False
            if force_period and self.nextcall > date_to:
                self.nextcall = date_to
                force_period = False
        return current_level, current_level_maximum_leave, force_period

    def _accrue_trailing_period(
        self, current_level, current_level_maximum_leave, leaves_taken
    ):
        """Credit the period the allocation has just entered.

        A plan that accrues at the start of a period owes the period it is in,
        which the step loop has not reached the end of.
        """
        self.check_singleton()
        level_start = {
            level._get_level_transition_date(self.date_from): level
            for level in self.accrual_plan_id.level_ids
        }
        current_level = (
            level_start.get(self.actual_lastcall)
            or current_level
            or self.accrual_plan_id.level_ids[0]
        )
        period_start = current_level._get_previous_anchor(self.actual_lastcall)
        if current_level.cap_accrued_time:
            current_level_maximum_leave = self._level_amount_in_days(
                current_level, current_level.maximum_leave
            )
        if self.actual_lastcall in {
            period_start,
            self.date_from,
        } | set(level_start.keys()) or (
            self.actual_lastcall
            - get_timedelta(
                current_level.accrual_validity_count,
                current_level.accrual_validity_type,
            )
            in {period_start, self.date_from} | set(level_start.keys())
        ):
            self._add_days_to_allocation(
                current_level,
                current_level_maximum_leave,
                leaves_taken,
                period_start,
                self.nextcall,
            )
            self.already_accrued = True

    def _process_accrual_plans(self, date_to=False, force_period=False, log=True):
        date_to = date_to or fields.Date.today()
        _debug.pipeline(
            "accrual_run",
            allocations=self,
            date_to=str(date_to),
            force_period=force_period,
        )
        already_accrued = {
            allocation.id: allocation.already_accrued
            or (
                allocation.number_of_days != 0
                and allocation.accrual_plan_id.accrued_gain_time == "start"
            )
            for allocation in self
        }
        for allocation in self:
            if allocation.allocation_type != "accrual":
                continue
            level_ids = allocation.accrual_plan_id.level_ids.sorted("sequence")
            if not level_ids:
                _debug.logic(
                    "accrual_skipped",
                    reason="plan_without_levels",
                    allocation=allocation,
                    plan=allocation.accrual_plan_id,
                )
                continue
            if allocation.holiday_status_id.request_unit in ["day", "half_day"]:
                leaves_taken = allocation.leaves_taken
            else:
                leaves_taken = (
                    allocation.leaves_taken
                    / allocation.employee_id._get_hours_per_day(allocation.date_from)
                )
            allocation.already_accrued = already_accrued[allocation.id]
            if (
                not allocation.nextcall
                and not allocation._update_initial_accrual_schedule(
                    level_ids, date_to, log
                )
            ):
                _debug.logic(
                    "accrual_skipped",
                    reason="not_seeded",
                    allocation=allocation,
                    levels=len(level_ids),
                )
                continue
            with _debug.perf(
                "accrual_steps",
                cr=self.env.cr,
                allocation=allocation,
                levels=len(level_ids),
                leaves_taken=leaves_taken,
            ) as span:
                current_level, current_level_maximum_leave, force_period = (
                    allocation._run_accrual_steps(
                        level_ids, date_to, force_period, leaves_taken
                    )
                )
                span.set(days=allocation.number_of_days, nextcall=allocation.nextcall)
            if allocation.accrual_plan_id.accrued_gain_time == "start":
                allocation._accrue_trailing_period(
                    current_level, current_level_maximum_leave, leaves_taken
                )

    def _get_accrual_step_date(self):
        self.check_singleton()
        if self.accrual_plan_id.accrued_gain_time != "end":
            return self.nextcall
        level, _level_idx = self._get_current_accrual_plan_level_id(self.nextcall)
        return level._get_anchor_day(self.nextcall) if level else self.nextcall

    @api.model
    def _update_accrual(self):
        tomorrow = datetime.combine(fields.Date.today() + relativedelta(days=1), time())
        allocations = self.search(
            [
                ("allocation_type", "=", "accrual"),
                ("state", "=", "validate"),
                ("accrual_plan_id", "!=", False),
                ("employee_id", "!=", False),
                "|",
                ("date_to", "=", False),
                ("date_to", ">", fields.Datetime.now()),
                "|",
                ("nextcall", "=", False),
                ("nextcall", "<=", tomorrow),
            ]
        )
        _debug.pipeline("accrual_cron", allocations=allocations)
        allocations._process_accrual_plans()

    def _get_future_leaves_on(self, accrual_date):
        self.check_singleton()
        if not accrual_date or accrual_date <= date.today():
            return 0

        if not (
            self.accrual_plan_id
            and self.state == "validate"
            and self.allocation_type == "accrual"
            and (not self.date_to or self.date_to > accrual_date)
            and (
                not self.nextcall
                or self.nextcall <= accrual_date + relativedelta(days=1)
            )
        ):
            return 0

        fake_allocation = (
            self.env["hr.leave.allocation"]
            .with_context(default_date_from=accrual_date)
            .new(origin=self)
        )
        fake_allocation.sudo()._process_accrual_plans(accrual_date, log=False)
        if self.holiday_status_id.request_unit == "hour":
            res = float_round(
                fake_allocation.number_of_hours_display - self.number_of_hours_display,
                precision_digits=2,
            )
        else:
            res = round((fake_allocation.number_of_days - self.number_of_days), 2)
        fake_allocation.invalidate_recordset()
        return res

    def _get_next_states_by_state(self):
        self.check_singleton()
        state_result = {
            "confirm": set(),
            "validate1": set(),
            "validate": set(),
            "refuse": set(),
        }
        validation_type = self.validation_type

        is_officer = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        is_time_off_manager = self.employee_id.leave_manager_id == self.env.user

        if is_officer:
            if validation_type == "both":
                state_result["confirm"].add("validate1")
                state_result["refuse"].add("validate1")
            state_result["validate1"].update({"confirm", "validate", "refuse"})
            state_result["confirm"].update({"validate", "refuse"})
            state_result["validate"].update({"confirm", "refuse"})
            state_result["refuse"].update({"confirm", "validate"})
        elif is_time_off_manager:
            if validation_type != "hr":
                state_result["confirm"].add("refuse")
                state_result["validate"].add("refuse")
            if validation_type == "both":
                state_result["confirm"].add("validate1")
                state_result["validate1"].add("refuse")
            elif validation_type == "manager":
                state_result["confirm"].add("validate")
                state_result["refuse"].add("validate")

        if validation_type == "no_validation":
            state_result["confirm"].add("validate")
        return state_result

    @api.depends(
        "employee_id", "holiday_status_id", "type_request_unit", "number_of_days"
    )
    def _compute_display_name(self):
        for allocation in self:
            allocation.display_name = _(
                "Allocation of %(leave_type)s: %(amount).2f %(unit)s to %(target)s",
                leave_type=allocation.holiday_status_id.sudo().name,
                amount=allocation.number_of_hours_display
                if allocation.type_request_unit == "hour"
                else allocation.number_of_days,
                unit=_("hours")
                if allocation.type_request_unit == "hour"
                else _("days"),
                target=allocation.employee_id.name,
            )

    def _add_lastcalls(self):
        for allocation in self:
            if allocation.allocation_type != "accrual":
                continue
            today = fields.Date.today()
            (current_level, current_level_idx) = (
                allocation._get_current_accrual_plan_level_id(today)
            )
            if not allocation.lastcall:
                if not current_level:
                    allocation.lastcall = today
                    allocation.actual_lastcall = allocation.lastcall
                    continue
                allocation.lastcall = max(
                    current_level._get_previous_anchor(today),
                    allocation.date_from
                    + get_timedelta(
                        current_level.start_count, current_level.start_type
                    ),
                )
                allocation.actual_lastcall = allocation.lastcall
            if current_level and not allocation.nextcall:
                accrual_plan = allocation.accrual_plan_id
                allocation.nextcall = current_level._get_next_anchor(
                    allocation.lastcall
                )
                if (
                    current_level_idx < (len(accrual_plan.level_ids) - 1)
                    and accrual_plan.transition_mode == "immediately"
                ):
                    next_level = accrual_plan.level_ids[current_level_idx + 1]
                    next_level_start = allocation.date_from + get_timedelta(
                        next_level.start_count, next_level.start_type
                    )
                    allocation.nextcall = min(allocation.nextcall, next_level_start)
                expiration_date = allocation.carried_over_days_expiration_date
                if expiration_date and expiration_date > allocation.lastcall:
                    allocation.nextcall = min(allocation.nextcall, expiration_date)

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if "state" in values and values["state"] != "confirm":
                _debug.logic(
                    "create_refused", reason="bad_state", state=values["state"]
                )
                raise UserError(_("Incorrect state for new allocation"))
        allocations = super(
            HrLeaveAllocation, self.with_context(mail_create_nosubscribe=True)
        ).create(vals_list)
        allocations._add_lastcalls()
        allocations.browse(
            allocation.id
            for allocation, values in zip(allocations, vals_list, strict=True)
            if "name" in values
        )._mark_custom_names()
        _debug.lifecycle("create", allocations=allocations, count=len(vals_list))
        for allocation in allocations:
            partners_to_subscribe = set()
            if allocation.employee_id.user_id:
                partners_to_subscribe.add(allocation.employee_id.user_id.partner_id.id)
            if allocation.validation_type == "hr":
                partners_to_subscribe.add(
                    allocation.employee_id.sudo().parent_id.user_id.partner_id.id
                )
                partners_to_subscribe.add(
                    allocation.employee_id.leave_manager_id.partner_id.id
                )
            allocation.message_subscribe(partner_ids=tuple(partners_to_subscribe))
            if not self.env.context.get("import_file"):
                allocation.activity_update()
            if (
                allocation.validation_type == "no_validation"
                and allocation.state == "confirm"
            ):
                allocation.action_approve()
        return allocations

    # Anything in here can leave already-taken leaves uncovered, so a write
    # touching one of them goes through the excess check below. `date_to`
    # included: pulling the end date in front of an approved leave strands it
    # just as surely as cutting the duration does.
    _COVERAGE_FIELDS = frozenset(
        {"number_of_days_display", "number_of_hours_display", "state", "date_to"}
    )

    def write(self, vals):
        values = vals
        employee_id = values.get("employee_id", False)
        if values.get("state"):
            self._check_approval_update(values["state"])
        if employee_id:
            self.add_follower(employee_id)

        changes_coverage = not self._COVERAGE_FIELDS.isdisjoint(values)
        excess_before = (
            self._excess_days_by_allocation() if changes_coverage else {}
        )
        result = super().write(values)
        if "name" in values:
            self._mark_custom_names()
        if "allocation_type" in values:
            self._add_lastcalls()
        if changes_coverage:
            self._check_duration_still_covers_leaves_taken(excess_before)
        return result

    def _excess_days_by_allocation(self):
        """Leave days each allocation's holder has taken beyond what it grants."""
        _consumed, extra_data = self.employee_id._get_consumed_leaves(
            leave_types=self.holiday_status_id
        )
        return {
            allocation.id: sum(
                excess["amount"]
                for excess in extra_data.get(allocation.employee_id, {})
                .get(allocation.holiday_status_id, {})
                .get("excess_days", {})
                .values()
                if not excess["is_virtual"]
            )
            for allocation in self
        }

    def _check_duration_still_covers_leaves_taken(self, excess_before):
        excess_after = self._excess_days_by_allocation()
        for allocation in self:
            before = excess_before.get(allocation.id, 0)
            after = excess_after.get(allocation.id, 0)
            if after <= before:
                continue
            leave_type = allocation.holiday_status_id
            if leave_type.allows_negative and after <= leave_type.max_allowed_negative:
                continue
            _debug.logic(
                "allocation_duration_refused",
                allocation=allocation,
                excess_before=before,
                excess_after=after,
                allows_negative=leave_type.allows_negative,
            )
            raise ValidationError(
                _(
                    "You cannot reduce the duration below the duration of leaves already taken by the employee."
                )
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_if_correct_states(self):
        if self.env.context.get("allocation_skip_state_check"):
            return
        state_description_values = self._state_labels()
        for allocation in self.filtered(
            lambda allocation: allocation.state not in ["confirm", "refuse"]
        ):
            raise UserError(
                _(
                    "You cannot delete an allocation request which is in %s state.",
                    state_description_values.get(allocation.state),
                )
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_leaves(self):
        if any(
            allocation.holiday_status_id.requires_allocation
            and allocation.leaves_taken > 0
            for allocation in self
        ):
            raise UserError(
                _(
                    "You cannot delete an allocation request which has some validated leaves."
                )
            )

    def action_approve(self):
        current_employee = self.env.user.employee_id
        allocation_to_approve = self.env["hr.leave.allocation"]
        allocation_to_validate = self.env["hr.leave.allocation"]
        for allocation in self:
            if allocation.can_validate:
                allocation_to_validate += allocation
            elif allocation.can_approve:
                allocation_to_approve += allocation
            else:
                _debug.logic(
                    "approve_refused", allocation=allocation, state=allocation.state
                )
                raise UserError(
                    _('Allocation must be "To Approve" in order to approve it.')
                )

        _debug.lifecycle(
            "approve",
            first_approval=allocation_to_approve,
            validated=allocation_to_validate,
        )
        allocation_to_approve.write(
            {"state": "validate1", "approver_id": current_employee.id}
        )
        allocation_to_validate._action_validate()
        self.activity_update()
        return True

    def _action_validate(self):
        current_employee = self.env.user.employee_id

        allocation_both = self.filtered(
            lambda allocation: allocation.validation_type == "both"
        )
        allocation_first_approve = allocation_both.filtered(
            lambda allocation: not allocation.approver_id
        )
        allocation_first_approve.write(
            {
                "state": "validate",
                "approver_id": current_employee.id,
                "second_approver_id": current_employee.id,
            }
        )
        (allocation_both - allocation_first_approve).write(
            {"state": "validate", "second_approver_id": current_employee.id}
        )
        _debug.lifecycle(
            "validate",
            both_first=allocation_first_approve,
            both_second=allocation_both - allocation_first_approve,
            single=self - allocation_both,
        )
        (self - allocation_both).write(
            {"state": "validate", "approver_id": current_employee.id}
        )

    def action_refuse(self):
        if any(
            allocation.state not in ["confirm", "validate", "validate1"]
            for allocation in self
        ):
            _debug.logic("refuse_refused", allocations=self)
            raise UserError(
                _(
                    "Allocation request must be confirmed, second approval or validated in order to refuse it."
                )
            )

        # `approver_id` holds whoever validated the allocation, so a refusal
        # leaves it alone rather than overwriting the real approver of one that
        # had been approved. The refusal itself is tracked on `state`.
        self.write({"state": "refuse"})
        self.activity_update()
        return True

    def _get_approval_precheck_error(self, state):
        if (
            self.employee_id == self.env.user.employee_id
            and self.holiday_status_id.allocation_validation_type != "no_validation"
            and not self.env.user.has_group("hr_holidays.group_hr_holidays_manager")
        ):
            return _(
                "Only a time off Administrator can approve/refuse their own requests."
            )
        return ""

    def _get_approval_transition_error(self, state, is_time_off_manager):
        if state == "confirm":
            return _(
                "You can't reset an allocation. Cancel/delete this one and create an other"
            )
        if state == "validate1":
            if not is_time_off_manager:
                return _("Only a Time Off Officer/Manager can approve an allocation.")
            return _("You can't approve a validated allocation.")
        if state == "validate":
            if not is_time_off_manager:
                return _("Only a Time Off Officer/Manager can validate an allocation.")
            if self.state == "refuse":
                return _("You can't approve this refused allocation.")
            return _(
                "You can only validate an allocation with validation by Time Off Manager."
            )
        if state == "refuse":
            if not is_time_off_manager:
                return _("Only a Time Off Officer/Manager can refuse an allocation.")
            return _(
                "You can't refuse an allocation with validation by Time Off Officer."
            )
        return ""

    def _get_approval_category_xmlid(self):
        return "hr_holidays.approval_category_allocation"

    def _get_approval_backfill_decider(self):
        return self.approver_id.user_id

    def _get_approval_sync_kinds(self):
        return {
            "confirm": "pending",
            "validate1": "progress",
            "validate": "approved",
            "refuse": "refused",
        }

    def _get_approval_outcome_states(self):
        return {
            "progress": "validate1",
            "approved": "validate",
            "refused": "refuse",
            "cancelled": "refuse",
        }

    def _apply_approval_state(self, state):
        self.check_singleton()
        if state == "validate1":
            self.write(
                {"state": "validate1", "approver_id": self.env.user.employee_id.id}
            )
        elif state == "validate":
            self._action_validate()
        elif state == "refuse":
            self.action_refuse()

    def _get_approval_activity_xmlids(self):
        return (
            "hr_holidays.mail_act_leave_allocation_approval",
            "hr_holidays.mail_act_leave_allocation_second_approval",
        )

    def _get_approval_activity_note(self):
        if self.state == "confirm":
            return _(
                "New Allocation Request created by %(user)s: %(count)s Days of %(allocation_type)s",
                user=self.create_uid.name,
                count=float_round(self.number_of_days, precision_digits=2),
                allocation_type=self.holiday_status_id.name,
            )
        return _(
            "Second approval request for %(allocation_type)s",
            allocation_type=self.holiday_status_id.name,
        )

    def _get_validated_notif_subtype(self):
        return self.holiday_status_id.allocation_notif_subtype_id or self.env.ref(
            "hr_holidays.mt_leave_allocation"
        )

    @api.model
    def open_pending_requests(self):
        user_employee = self.env.user.employee_id
        employee = self.env["hr.employee"]._get_contextual_employee()
        context = {
            "search_default_approve": True,
            "search_default_second_approval": True,
        }
        domain = []
        if employee != user_employee:
            view_name = "hr_holidays.hr_leave_allocation_view_tree"
            context.update({"search_default_employee_id": employee.id})
        else:
            view_name = "hr_holidays.hr_leave_allocation_view_tree_my"
            domain = [("employee_id", "=", employee.id)]
        return {
            "name": _("Allocation Requests"),
            "type": "ir.actions.act_window",
            "res_model": "hr.leave.allocation",
            "views": [[self.env.ref(view_name).id, "list"]],
            "domain": domain,
            "context": context,
        }

    @api.onchange("allocation_type")
    def _onchange_allocation_type(self):
        if self.allocation_type == "accrual":
            self.number_of_days = 0.0
        elif not self.number_of_days_display:
            self.number_of_days = 1.0

    @api.onchange("date_from", "accrual_plan_id", "date_to", "employee_id")
    def _onchange_date_from(self):
        if (
            not self.date_from
            or self.allocation_type != "accrual"
            or self.state == "validate"
            or not self.accrual_plan_id
            or not self.employee_id
        ):
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
