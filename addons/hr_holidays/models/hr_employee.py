from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta

from dateutil.relativedelta import relativedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_round

from odoo.addons.resource.models.utils import HOURS_PER_DAY

_FIRST_WORKING_INTERVAL_LOOKAHEAD_DAYS = (7, 30, 90, 180, 365, 730)


_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    leave_manager_id = fields.Many2one(
        comodel_name="res.users",
        string="Time Off Approver",
        compute="_compute_leave_manager_id",
        store=True,
        readonly=False,
        domain="[('share', '=', False), ('company_ids', 'in', company_id)]",
        help='Select the user responsible for approving "Time Off" of this employee.\n'
        "If empty, the approval is done by an Administrator or Approver (determined in settings/users).",
    )
    leave_ids = fields.One2many(
        comodel_name="hr.leave",
        inverse_name="employee_id",
        string="Time Off",
        groups="hr.group_hr_user",
    )
    current_leave_id = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Current Time Off Type",
        compute="_compute_current_leave_id",
        groups="hr.group_hr_user",
    )
    current_leave_state = fields.Selection(
        selection=[
            ("confirm", "Waiting Approval"),
            ("refuse", "Refused"),
            ("validate1", "Waiting Second Approval"),
            ("validate", "Approved"),
            ("cancel", "Cancelled"),
        ],
        string="Current Time Off Status",
        compute="_compute_leave_status",
        groups="hr.group_hr_user",
    )
    leave_date_from = fields.Date(
        string="From Date",
        compute="_compute_leave_status",
        groups="hr.group_hr_user",
    )
    leave_date_to = fields.Date(
        string="To Date",
        compute="_compute_leave_status",
    )
    allocation_count = fields.Float(
        string="Total number of days allocated.",
        compute="_compute_allocation_counts",
        groups="hr.group_hr_user",
    )
    allocations_count = fields.Integer(
        string="Total number of allocations",
        compute="_compute_allocation_counts",
        groups="hr.group_hr_user",
    )
    show_leaves = fields.Boolean(
        string="Able to see Remaining Time Off",
        compute="_compute_show_leaves",
    )
    is_absent = fields.Boolean(
        string="Absent Today",
        compute="_compute_leave_status",
        search="_search_is_absent",
    )
    allocation_display = fields.Char(compute="_compute_allocation_displays")
    allocation_remaining_display = fields.Char(compute="_compute_allocation_displays")
    hr_icon_display = fields.Selection(
        selection_add=[
            ("presence_holiday_absent", "On leave"),
            ("presence_holiday_present", "Present but on leave"),
        ]
    )

    @api.depends(
        "leave_ids.state",
        "leave_ids.date_from",
        "leave_ids.date_to",
        "leave_ids.holiday_status_id",
    )
    def _compute_current_leave_id(self):
        self.current_leave_id = False

        holidays = (
            self.env["hr.leave"]
            .sudo()
            .search(
                [
                    ("employee_id", "in", self.ids),
                    ("date_from", "<=", fields.Datetime.now()),
                    ("date_to", ">=", fields.Datetime.now()),
                    ("state", "=", "validate"),
                ]
            )
        )
        leave_type_by_employee = {
            holiday.employee_id.id: holiday.holiday_status_id.id for holiday in holidays
        }
        for employee in self.filtered(lambda e: e.id in leave_type_by_employee):
            employee.current_leave_id = leave_type_by_employee[employee.id]

    @api.depends("is_absent")
    def _compute_hr_presence_state(self):
        super()._compute_hr_presence_state()
        employees = self.filtered(
            lambda employee: (
                employee.hr_presence_state != "present" and employee.is_absent
            )
        )
        employees.update({"hr_presence_state": "absent"})

    def _compute_allocation_counts(self):
        current_date = fields.Date.context_today(self)
        data = self.env["hr.leave.allocation"]._read_group(
            [
                ("employee_id", "in", self.ids),
                ("holiday_status_id.active", "=", True),
                ("holiday_status_id.requires_allocation", "=", True),
                ("state", "=", "validate"),
                ("date_from", "<=", current_date),
                "|",
                ("date_to", "=", False),
                ("date_to", ">=", current_date),
            ],
            ["employee_id"],
            ["__count", "number_of_days:sum"],
        )
        rg_results = {employee.id: (count, days) for employee, count, days in data}
        for employee in self:
            count, days = rg_results.get(employee.id, (0, 0))
            employee.allocation_count = float_round(days, precision_digits=2)
            employee.allocations_count = count

    def _compute_allocation_displays(self):
        current_date = fields.Date.context_today(self)
        allocations = self.env["hr.leave.allocation"].search(
            [("employee_id", "in", self.ids)]
        )
        leaves_taken = self._get_consumed_leaves(allocations.holiday_status_id)[0]
        for employee in self:
            employee_remaining_leaves = 0
            employee_max_leaves = 0
            for leave_type in leaves_taken[employee]:
                if (
                    not leave_type.requires_allocation
                    or leave_type.hide_on_dashboard
                    or not leave_type.active
                ):
                    continue
                for allocation in leaves_taken[employee][leave_type]:
                    if (
                        allocation
                        and allocation.date_from <= current_date
                        and (
                            not allocation.date_to or allocation.date_to >= current_date
                        )
                    ):
                        virtual_remaining_leaves = leaves_taken[employee][leave_type][
                            allocation
                        ]["virtual_remaining_leaves"]
                        employee_remaining_leaves += (
                            virtual_remaining_leaves
                            if leave_type.request_unit in ["day", "half_day"]
                            else virtual_remaining_leaves
                            / (
                                employee.resource_calendar_id.hours_per_day
                                or HOURS_PER_DAY
                            )
                        )
                        employee_max_leaves += allocation.number_of_days
            employee.allocation_remaining_display = "%g" % float_round(
                employee_remaining_leaves, precision_digits=2
            )
            employee.allocation_display = "%g" % float_round(
                employee_max_leaves, precision_digits=2
            )

    @api.depends("is_absent")
    def _compute_presence_icon(self):
        super()._compute_presence_icon()
        employees_absent = self.filtered(
            lambda employee: (
                employee.hr_presence_state != "present" and employee.is_absent
            )
        )
        employees_absent.update(
            {"hr_icon_display": "presence_holiday_absent", "show_hr_icon_display": True}
        )
        employees_present = self.filtered(
            lambda employee: (
                employee.hr_presence_state == "present" and employee.is_absent
            )
        )
        employees_present.update(
            {
                "hr_icon_display": "presence_holiday_present",
                "show_hr_icon_display": True,
            }
        )

    def _get_first_working_interval(self, dt):
        self.check_singleton()
        return self._get_first_working_interval_batch({self.id: dt})[self.id]

    def _calendar_windows_from(self, start_by_employee_id, lookahead_days):
        """Group the employees' search windows by the calendar that answers them.

        A window is a calendar period clipped to the employee's own
        ``[start, start + lookahead_days]``. Periods that clip to nothing are
        dropped: ``_get_calendar_periods`` clamps both ends to the requested
        range, so a version starting after it comes back inverted.
        """
        starts = {
            employee: start_by_employee_id[employee.id].replace(tzinfo=UTC)
            for employee in self
        }
        stops = {
            employee: start + timedelta(days=lookahead_days)
            for employee, start in starts.items()
        }
        periods_by_employee = self._get_calendar_periods(
            min(starts.values()), max(stops.values())
        )
        windows_by_calendar = defaultdict(list)
        for employee in self:
            start, stop = starts[employee], stops[employee]
            periods = periods_by_employee.get(employee) or [
                (start, stop, employee.resource_calendar_id)
            ]
            for period_start, period_stop, calendar in periods:
                calendar = calendar or employee.company_id.resource_calendar_id
                window = (max(period_start, start), min(period_stop, stop))
                if calendar and window[0] < window[1]:
                    windows_by_calendar[calendar].append((employee, *window))
        return windows_by_calendar

    def _first_working_moment(self, intervals, start, stop):
        """The first moment in ``[start, stop)`` the resource is working.

        An interval that already contains ``start`` answers ``start`` itself:
        the employee is at work then. Reading the interval's own beginning
        instead would make the answer depend on where the batch happened to
        begin, because that is the only thing clipping it.
        """
        for interval_start, interval_stop, _meta in intervals:
            if interval_stop <= start:
                continue
            if interval_start >= stop:
                return None
            return max(interval_start, start)
        return None

    def _cluster_windows(self, windows, lookahead_days):
        """Group windows so that no batched question spans much more than the
        lookahead it was asked for.

        One employee whose leave ends a year out would otherwise make every
        other employee on the same calendar pay for a year of attendance
        intervals to answer a seven-day question.
        """
        span = timedelta(days=2 * lookahead_days)
        clusters = []
        for window in sorted(windows, key=lambda window: window[1]):
            if clusters and window[2] - clusters[-1][0][1] <= span:
                clusters[-1].append(window)
            else:
                clusters.append([window])
        return clusters

    def _get_first_working_interval_batch(self, start_by_employee_id):
        """Map each employee id to the start of its first working interval at or
        after that employee's datetime, or None when it finds none in two years.

        Every calendar is asked once per cluster of employees looking at nearby
        dates -- the same question asked per employee costs one
        ``_work_intervals_batch`` each.
        """
        result = dict.fromkeys(start_by_employee_id)
        pending = self.filtered(
            lambda employee: employee.id in start_by_employee_id
        ).sudo()
        for lookahead_days in _FIRST_WORKING_INTERVAL_LOOKAHEAD_DAYS:
            if not pending:
                break
            windows_by_calendar = pending._calendar_windows_from(
                start_by_employee_id, lookahead_days
            )
            found = {}
            batches = 0
            for calendar, windows in windows_by_calendar.items():
                for cluster in self._cluster_windows(windows, lookahead_days):
                    batches += 1
                    intervals = calendar._work_intervals_batch(
                        cluster[0][1],
                        max(stop for _employee, _start, stop in cluster),
                        resources=self.env["resource.resource"].union(
                            *(
                                employee.resource_id
                                for employee, _start, _stop in cluster
                            )
                        ),
                    )
                    for employee, start, stop in cluster:
                        moment = self._first_working_moment(
                            intervals.get(employee.resource_id.id, ()), start, stop
                        )
                        if moment is not None:
                            earliest = found.get(employee.id)
                            if earliest is None or moment < earliest:
                                found[employee.id] = moment
            _debug.logic(
                "first_working_interval_batch",
                employees=pending,
                lookahead_days=lookahead_days,
                batches=batches,
                answered=len(found),
                pending=len(pending),
            )
            result.update(found)
            pending = pending.filtered(
                lambda employee, found=found: employee.id not in found
            )
        return result

    @api.depends(
        "leave_ids.state",
        "leave_ids.date_from",
        "leave_ids.date_to",
        "leave_ids.holiday_status_id.time_type_id.is_work",
    )
    def _compute_leave_status(self):
        holidays = (
            self.env["hr.leave"]
            .sudo()
            .search(
                [
                    ("employee_id", "in", self.ids),
                    ("date_from", "<=", fields.Datetime.now()),
                    ("date_to", ">=", fields.Datetime.now()),
                    ("holiday_status_id.time_type_id.is_work", "=", False),
                    ("state", "=", "validate"),
                ]
            )
        )
        leave_by_employee_id = {holiday.employee_id.id: holiday for holiday in holidays}
        back_on_by_employee_id = holidays.employee_id._get_first_working_interval_batch(
            {
                employee_id: holiday.date_to
                for employee_id, holiday in leave_by_employee_id.items()
            }
        )
        for employee in self:
            holiday = leave_by_employee_id.get(employee.id)
            back_on = back_on_by_employee_id.get(employee.id)
            employee.leave_date_from = holiday.date_from.date() if holiday else False
            employee.leave_date_to = back_on.date() if back_on else False
            employee.current_leave_state = holiday.state if holiday else False
            employee.is_absent = bool(holiday) and holiday.state == "validate"

    @api.depends("parent_id")
    def _compute_leave_manager_id(self):
        for employee in self:
            previous_manager = employee._origin.parent_id.user_id
            manager = employee.parent_id.user_id
            if (
                manager and employee.leave_manager_id == previous_manager
            ) or not employee.leave_manager_id:
                employee.leave_manager_id = manager

    @api.depends_context("uid")
    def _compute_show_leaves(self):
        show_leaves = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        for employee in self:
            if show_leaves or employee.user_id == self.env.user:
                employee.show_leaves = True
            else:
                employee.show_leaves = False

    def _search_is_absent(self, operator, value):
        if operator != "in":
            return NotImplemented
        today_start = date.today()
        today_end = today_start + timedelta(1)
        holidays = (
            self.env["hr.leave"]
            .sudo()
            .search(
                [
                    ("employee_id", "!=", False),
                    ("state", "=", "validate"),
                    ("date_from", "<", today_end),
                    ("date_to", ">=", today_start),
                ]
            )
        )
        if True in value and False in value:
            return Domain.TRUE
        return [("id", "in" if True in value else "not in", holidays.employee_id.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("salary_simulation"):
            return super().create(vals_list)
        approver_group = self.env.ref(
            "hr_holidays.group_hr_holidays_responsible", raise_if_not_found=False
        )
        group_updates = []
        for vals in vals_list:
            if "parent_id" in vals:
                manager = self.env["hr.employee"].browse(vals["parent_id"]).user_id
                vals["leave_manager_id"] = vals.get("leave_manager_id", manager.id)
            if approver_group and vals.get("leave_manager_id"):
                group_updates.append(Command.link(vals["leave_manager_id"]))
        if group_updates:
            approver_group.sudo().write({"user_ids": group_updates})
        return super().create(vals_list)

    def write(self, vals):
        values = vals
        # Read the caller's flag before setting our own: this method re-enters
        # itself through the `leave_manager_id` write below, and the guard is
        # there to stop that recursion -- not to stop the resync it is tested
        # against further down, which is what happened when the two were read
        # from the same context.
        resync_leaves = not self.env.context.get("no_leave_resource_calendar_update")
        self = self.with_context(no_leave_resource_calendar_update=True)
        if "parent_id" in values:
            manager = self.env["hr.employee"].browse(values["parent_id"]).user_id
            if manager:
                to_change = self.filtered(
                    lambda e: (
                        e.leave_manager_id == e.parent_id.user_id
                        or not e.leave_manager_id
                    )
                )
                to_change.write(
                    {"leave_manager_id": values.get("leave_manager_id", manager.id)}
                )

        old_managers = self.env["res.users"]
        if "leave_manager_id" in values:
            old_managers = self.mapped("leave_manager_id")
            if values["leave_manager_id"]:
                leave_manager = self.env["res.users"].browse(values["leave_manager_id"])
                old_managers -= leave_manager
                approver_group = self.env.ref(
                    "hr_holidays.group_hr_holidays_responsible",
                    raise_if_not_found=False,
                )
                if approver_group and not leave_manager.has_group(
                    "hr_holidays.group_hr_holidays_responsible"
                ):
                    leave_manager.sudo().write(
                        {"group_ids": [Command.link(approver_group.id)]}
                    )

        res = super().write(values)
        old_managers.sudo()._clean_leave_responsible_users()

        if "resource_calendar_id" in values and resync_leaves:
            try:
                leaves = self.env["hr.leave"].search(
                    [
                        ("employee_id", "in", self.ids),
                        (
                            "resource_calendar_id",
                            "!=",
                            int(values["resource_calendar_id"]),
                        ),
                        ("date_from", ">", fields.Datetime.now()),
                    ]
                )
                leaves.write({"resource_calendar_id": values["resource_calendar_id"]})
                non_hourly_leaves = leaves.filtered(lambda l: not l.request_unit_hours)
                non_hourly_leaves.with_context(
                    leave_skip_date_check=True, leave_skip_state_check=True
                )._compute_date_from_to()
                non_hourly_leaves.filtered(
                    lambda l: l.state == "validate"
                )._apply_leave_request()
            except ValidationError as e:
                raise ValidationError(
                    _(
                        "Changing this working schedule results in the affected employee(s) not having enough "
                        "leaves allocated to accomodate for their leaves already taken in the future. Please "
                        "review this employee's leaves and adjust their allocation accordingly."
                    )
                ) from e

        if "parent_id" in values or "department_id" in values:
            today_date = fields.Datetime.now()
            hr_vals = {}
            if values.get("department_id") is not None:
                hr_vals["department_id"] = values["department_id"]
            holidays = (
                self.env["hr.leave"]
                .sudo()
                .search(
                    [
                        "|",
                        ("state", "=", "confirm"),
                        ("date_from", ">", today_date),
                        ("employee_id", "in", self.ids),
                    ]
                )
            )
            if hr_vals:
                holidays.write(hr_vals)
            if values.get("parent_id") is not None:
                hr_vals["manager_id"] = values["parent_id"]
            allocations = (
                self.env["hr.leave.allocation"]
                .sudo()
                .search(
                    [
                        ("state", "=", "confirm"),
                        ("employee_id", "in", self.ids),
                    ]
                )
            )
            allocations.write(hr_vals)
        return res

    def _get_user_field_names_to_empty_on_archive(self):
        return super()._get_user_field_names_to_empty_on_archive() + [
            "leave_manager_id"
        ]

    def action_time_off_dashboard(self):
        return {
            "name": _("Time Off Dashboard"),
            "type": "ir.actions.act_window",
            "res_model": "hr.leave",
            "views": [
                [
                    self.env.ref("hr_holidays.hr_leave_employee_view_dashboard").id,
                    "calendar",
                ]
            ],
            "domain": [("employee_id", "in", self.ids)],
            "context": {
                "employee_id": self.ids,
            },
        }

    def get_mandatory_days(self, start_date, end_date):
        all_days = {}

        self = self or self.env.user.employee_id

        mandatory_days = self._get_mandatory_days(start_date, end_date)
        for mandatory_day in mandatory_days:
            num_days = (mandatory_day.end_date - mandatory_day.start_date).days
            for d in range(num_days + 1):
                all_days[str(mandatory_day.start_date + relativedelta(days=d))] = (
                    mandatory_day.color
                )

        return all_days

    @api.model
    def get_special_days_data(self, date_start, date_end):
        return {
            "mandatoryDays": self.get_mandatory_days_data(date_start, date_end),
            "bankHolidays": self.get_public_holidays_data(date_start, date_end),
        }

    @api.model
    def get_public_holidays_data(self, date_start, date_end):
        self = self._get_contextual_employee()
        employee_tz = timezone(
            self._get_schedule_tz() if self else self.env.user.tz or "utc"
        )
        public_holidays = self._get_public_holidays(date_start, date_end).sorted(
            "date_from"
        )
        return [
            {
                "id": -bh.id,
                "colorIndex": 0,
                "end": datetime.combine(
                    bh.date_to.astimezone(employee_tz), datetime.max.time()
                ).isoformat(),
                "endType": "datetime",
                "isAllDay": True,
                "start": datetime.combine(
                    bh.date_from.astimezone(employee_tz), datetime.min.time()
                ).isoformat(),
                "startType": "datetime",
                "title": bh.name,
            }
            for bh in public_holidays
        ]

    @api.model
    def get_time_off_dashboard_data(self, target_date=None):
        dashboard_data = {}
        dashboard_data["has_accrual_allocation"] = self.env[
            "hr.leave.type"
        ].has_accrual_allocation()
        dashboard_data["allocation_data"] = self.env[
            "hr.leave.type"
        ].get_allocation_data_request(target_date, False)
        dashboard_data["allocation_request_amount"] = (
            self.get_allocation_requests_amount()
        )
        return dashboard_data

    @api.model
    def get_allocation_requests_amount(self):
        employee = self._get_contextual_employee()
        return self.env["hr.leave.allocation"].search_count(
            [
                ("employee_id", "=", employee.id),
                ("state", "=", "confirm"),
            ]
        )

    def _calendar_companies(self):
        """The companies a calendar screen about this employee may read.

        The one the employee belongs to, and nothing else -- which is already
        what the day grid does, through the company `hr.employee._get_unusual_days`
        hands to `resource.calendar`. Reading `env.companies` instead let a
        sister company's days land on this employee's calendar, and made the
        grid and the side panel of the same screen disagree about a day.
        """
        return self.company_id or self.env.company

    def _get_public_holidays(self, date_start, date_end):
        leaves = self.env["resource.schedule.exception"]
        return leaves.search(
            leaves._get_domain_public_holidays(
                date_start,
                date_end,
                companies=self._calendar_companies(),
                calendars=self.resource_calendar_id,
            )
        )

    @api.model
    def get_mandatory_days_data(self, date_start, date_end):
        self_with_context = self._get_contextual_employee()
        if isinstance(date_start, str):
            date_start = datetime.fromisoformat(date_start).replace(tzinfo=None)
        elif isinstance(date_start, datetime):
            date_start = date_start.replace(tzinfo=None)

        if isinstance(date_end, str):
            date_end = datetime.fromisoformat(date_end).replace(tzinfo=None)
        elif isinstance(date_end, datetime):
            date_end = date_end.replace(tzinfo=None)

        mandatory_days = self_with_context._get_mandatory_days(
            date_start, date_end
        ).sorted("start_date")
        return [
            {
                "id": -sd.id,
                "colorIndex": sd.color,
                "end": datetime.combine(sd.end_date, datetime.max.time()).isoformat(),
                "endType": "datetime",
                "isAllDay": True,
                "start": datetime.combine(
                    sd.start_date, datetime.min.time()
                ).isoformat(),
                "startType": "datetime",
                "title": sd.name,
            }
            for sd in mandatory_days
        ]

    def _get_mandatory_days(self, start_date, end_date):
        domain = [
            ("start_date", "<=", end_date),
            ("end_date", ">=", start_date),
            ("company_id", "in", self._calendar_companies().ids),
            "|",
            ("resource_calendar_id", "=", False),
            ("resource_calendar_id", "in", self.resource_calendar_id.ids),
        ]

        if self.job_id:
            domain += [
                ("job_ids", "in", [False] + self.job_id.ids),
            ]
        if self.department_id:
            department_ids = self.department_id.ids
            domain += [
                "|",
                ("department_ids", "=", False),
                ("department_ids", "parent_of", department_ids),
            ]
        else:
            domain += [("department_ids", "=", False)]

        return self.env["hr.leave.mandatory.day"].search(domain)

    @api.model
    def _get_contextual_employee(self):
        """The one employee the screen in context is about.

        The key arrives as an id or as a list of them -- a form button sends
        its record, `action_time_off_dashboard` sends its whole selection so
        the calendar can filter on it -- while every reader here wants one
        employee and raises `Expected singleton` given more.
        """
        ctx = self.env.context
        for key in ("employee_id", "default_employee_id"):
            if ctx.get(key) is not None:
                return self.browse(ctx[key])[:1]
        return self.env.user.employee_id[:1]

    def _get_consumed_leaves(self, leave_types, target_date=False, ignore_future=False):
        employees = self or self._get_contextual_employee()
        leaves_domain = [
            ("holiday_status_id", "in", leave_types.ids),
            ("employee_id", "in", employees.ids),
            ("state", "in", ["confirm", "validate1", "validate"]),
        ]
        if self.env.context.get("ignored_leave_ids"):
            _debug.logic(
                "consumed_leaves_ignoring",
                ignored=len(self.env.context["ignored_leave_ids"]),
            )
            leaves_domain.append(
                ("id", "not in", self.env.context.get("ignored_leave_ids"))
            )

        if not target_date:
            target_date = fields.Date.context_today(self)
        if ignore_future:
            leaves_domain.append(("date_from", "<=", target_date))
        leaves = self.env["hr.leave"].search(leaves_domain)
        leaves_per_employee_type = defaultdict(
            lambda: defaultdict(lambda: self.env["hr.leave"])
        )
        for leave in leaves:
            leaves_per_employee_type[leave.employee_id][leave.holiday_status_id] |= (
                leave
            )

        allocations = (
            self.env["hr.leave.allocation"]
            .with_context(active_test=False)
            .search(
                [
                    ("employee_id", "in", employees.ids),
                    ("holiday_status_id", "in", leave_types.ids),
                    ("state", "=", "validate"),
                ]
            )
        )
        _debug.perf.count(
            "consumed_leaves_scanned",
            employees=employees,
            types=leave_types,
            leaves=leaves,
            allocations=allocations,
            target_date=str(target_date),
            ignore_future=ignore_future,
        )
        allocations_per_employee_type = defaultdict(
            lambda: defaultdict(lambda: self.env["hr.leave.allocation"])
        )
        for allocation in allocations:
            allocations_per_employee_type[allocation.employee_id][
                allocation.holiday_status_id
            ] |= allocation

        allocations_leaves_consumed = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0)))
        )

        to_recheck_leaves_per_leave_type = defaultdict(
            lambda: defaultdict(
                lambda: {
                    "excess_days": defaultdict(
                        lambda: {
                            "amount": 0,
                            "is_virtual": True,
                        }
                    ),
                    "exceeding_duration": 0,
                    "to_recheck_leaves": self.env["hr.leave"],
                }
            )
        )
        for allocation in allocations:
            allocation_data = allocations_leaves_consumed[allocation.employee_id][
                allocation.holiday_status_id
            ][allocation]
            future_leaves = 0
            if allocation.allocation_type == "accrual":
                future_leaves = allocation._get_future_leaves_on(target_date)
            max_leaves = (
                allocation.number_of_hours_display
                if allocation.holiday_status_id.request_unit == "hour"
                else allocation.number_of_days_display
            )
            max_leaves += future_leaves
            allocation_data.update(
                {
                    "max_leaves": max_leaves,
                    "accrual_bonus": future_leaves,
                    "virtual_remaining_leaves": max_leaves,
                    "remaining_leaves": max_leaves,
                    "leaves_taken": 0,
                    "virtual_leaves_taken": 0,
                }
            )

        for employee in employees:
            for leave_type in leave_types:
                allocations_with_date_to = self.env["hr.leave.allocation"]
                allocations_without_date_to = self.env["hr.leave.allocation"]
                for leave_allocation in allocations_per_employee_type[employee][
                    leave_type
                ]:
                    if leave_allocation.date_to:
                        allocations_with_date_to |= leave_allocation
                    else:
                        allocations_without_date_to |= leave_allocation
                sorted_leave_allocations = (
                    allocations_with_date_to.sorted(key="date_to")
                    + allocations_without_date_to
                )

                if leave_type.request_unit in ["day", "half_day"]:
                    leave_duration_field = "number_of_days"
                    leave_unit = "days"
                else:
                    leave_duration_field = "number_of_hours"
                    leave_unit = "hours"

                leave_type_data = allocations_leaves_consumed[employee][leave_type]
                for leave in leaves_per_employee_type[employee][leave_type].sorted(
                    "date_from"
                ):
                    leave_duration = leave[leave_duration_field]

                    if (
                        leave.date_from.date() > target_date
                        and sorted_leave_allocations.filtered(
                            lambda a, leave=leave: (
                                a.allocation_type == "accrual"
                                and (not a.date_to or a.date_to >= target_date)
                                and a.date_from <= leave.date_to.date()
                            )
                        )
                    ):
                        to_recheck_leaves_per_leave_type[employee][leave_type][
                            "to_recheck_leaves"
                        ] |= leave
                        continue

                    if leave_type.requires_allocation:
                        for allocation in sorted_leave_allocations:
                            if allocation.date_from > leave.date_to.date() or (
                                allocation.date_to
                                and allocation.date_to < leave.date_from.date()
                            ):
                                continue
                            interval_start = max(
                                leave.date_from,
                                datetime.combine(allocation.date_from, time.min),
                            )
                            interval_end = min(
                                leave.date_to,
                                datetime.combine(allocation.date_to, time.max)
                                if allocation.date_to
                                else leave.date_to,
                            )
                            duration = leave[leave_duration_field]
                            if (
                                leave.date_from != interval_start
                                or leave.date_to != interval_end
                            ):
                                duration_info = employee._get_calendar_attendances(
                                    interval_start.replace(tzinfo=UTC),
                                    interval_end.replace(tzinfo=UTC),
                                )
                                duration = duration_info[
                                    "hours" if leave_unit == "hours" else "days"
                                ]
                            max_allowed_duration = min(
                                duration,
                                leave_type_data[allocation]["virtual_remaining_leaves"],
                            )

                            if not max_allowed_duration:
                                continue

                            allocated_time = min(max_allowed_duration, leave_duration)
                            leave_type_data[allocation]["virtual_leaves_taken"] += (
                                allocated_time
                            )
                            leave_type_data[allocation]["virtual_remaining_leaves"] -= (
                                allocated_time
                            )
                            if leave.state == "validate":
                                leave_type_data[allocation]["leaves_taken"] += (
                                    allocated_time
                                )
                                leave_type_data[allocation]["remaining_leaves"] -= (
                                    allocated_time
                                )

                            leave_duration -= allocated_time
                            if not leave_duration:
                                break
                        if round(leave_duration, 2) > 0:
                            to_recheck_leaves_per_leave_type[employee][leave_type][
                                "excess_days"
                            ][(leave.date_to.date(), leave.id)] = {
                                "amount": leave_duration,
                                "is_virtual": leave.state != "validate",
                                "leave_id": leave.id,
                            }
                    else:
                        if leave_unit == "hours":
                            allocated_time = leave.number_of_hours
                        else:
                            allocated_time = leave.number_of_days
                        leave_type_data[False]["virtual_leaves_taken"] += allocated_time
                        leave_type_data[False]["virtual_remaining_leaves"] = 0
                        leave_type_data[False]["remaining_leaves"] = 0
                        if leave.state == "validate":
                            leave_type_data[False]["leaves_taken"] += allocated_time
        for employee in to_recheck_leaves_per_leave_type:
            for leave_type in to_recheck_leaves_per_leave_type[employee]:
                content = to_recheck_leaves_per_leave_type[employee][leave_type]
                consumed_content = allocations_leaves_consumed[employee][leave_type]
                if content["to_recheck_leaves"]:
                    date_to_simulate = max(
                        content["to_recheck_leaves"].mapped("date_from")
                    ).date()
                    latest_accrual_bonus = 0
                    date_accrual_bonus = 0
                    virtual_remaining = 0
                    additional_leaves_duration = 0
                    for allocation in consumed_content:
                        latest_accrual_bonus += (
                            allocation
                            and allocation._get_future_leaves_on(date_to_simulate)
                        )
                        date_accrual_bonus += consumed_content[allocation][
                            "accrual_bonus"
                        ]
                        virtual_remaining += consumed_content[allocation][
                            "virtual_remaining_leaves"
                        ]
                    for leave in content["to_recheck_leaves"]:
                        additional_leaves_duration += (
                            leave.number_of_hours
                            if leave_type.request_unit == "hour"
                            else leave.number_of_days
                        )
                    latest_remaining = (
                        virtual_remaining - date_accrual_bonus + latest_accrual_bonus
                    )
                    content["exceeding_duration"] = round(
                        min(0, latest_remaining - additional_leaves_duration), 2
                    )

        return (allocations_leaves_consumed, to_recheck_leaves_per_leave_type)

    def _get_duration_until(self, date_from, date_to):
        self.check_singleton()
        start_datetime = datetime.combine(date_from, time.min).replace(tzinfo=UTC)
        end_datetime = datetime.combine(date_to, time.max).replace(tzinfo=UTC)
        calendar = self.resource_calendar_id
        if not calendar:
            return {
                "hours": float_round(
                    (end_datetime - start_datetime).total_seconds() / 3600,
                    precision_rounding=0.001,
                ),
                "days": (end_datetime - start_datetime).days + 1,
            }
        intervals = calendar._work_intervals_batch(
            start_datetime, end_datetime, resources=self.resource_id
        )
        return calendar._get_attendance_intervals_days_data(
            intervals[self.resource_id.id]
        )

    def _get_hours_per_day(self, date_from):
        if not self:
            return 0
        calendars = self._get_calendars(date_from)
        return calendars[self.id].hours_per_day if calendars[self.id] else 24

    def _get_fields_store_avatar_card(self, target):
        return [*super()._get_fields_store_avatar_card(target), "leave_date_to"]
