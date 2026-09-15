from collections import defaultdict
from contextlib import contextmanager
from datetime import UTC, datetime, time, timedelta
from itertools import chain, pairwise

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.datetime import timezone
from odoo.libs.intervals import Intervals
from odoo.tools import convert, format_datetime, format_duration, format_time
from odoo.tools.date_utils import get_intervals_hours

from ..tools import debug_log as dbg
from ..tools import demo


def get_google_maps_url(latitude, longitude):
    return "https://maps.google.com?q=%s,%s" % (latitude, longitude)


class HrAttendance(models.Model):
    _name = "hr.attendance"
    _description = "Attendance"
    _order = "check_in desc"
    _inherit = ["mixin.mail.thread"]

    def _default_employee_id(self):
        if self.env.user.has_group("hr_attendance.group_hr_attendance_user"):
            return self.env.user.employee_id
        return None

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        default=_default_employee_id,
        index=True,
        required=True,
        group_expand="_read_group_employee_id",
        ondelete="cascade",
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        related="employee_id.department_id",
        string="Department",
        readonly=True,
    )
    manager_id = fields.Many2one(
        comodel_name="hr.employee",
        related="employee_id.parent_id",
        export_string_translation=False,
        readonly=True,
    )
    attendance_manager_id = fields.Many2one(
        comodel_name="res.users",
        related="employee_id.attendance_manager_id",
        export_string_translation=False,
    )
    is_manager = fields.Boolean(compute="_compute_is_manager")
    check_in = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
        required=True,
        tracking=True,
    )
    check_out = fields.Datetime(tracking=True)
    date = fields.Date(
        compute="_compute_date",
        precompute=True,
        store=True,
        index=True,
        required=True,
    )
    worked_hours = fields.Float(
        compute="_compute_worked_hours",
        store=True,
        readonly=True,
    )
    color = fields.Integer(compute="_compute_color")
    overtime_hours = fields.Float(
        string="Over Time",
        compute="_compute_overtime_hours",
        store=True,
    )
    overtime_status = fields.Selection(
        selection=[
            ("to_approve", "To Approve"),
            ("approved", "Approved"),
            ("refused", "Refused"),
        ],
        compute="_compute_overtime_status",
        store=True,
        readonly=False,
        tracking=True,
    )
    validated_overtime_hours = fields.Float(
        string="Extra Hours",
        compute="_compute_validated_overtime_hours",
        store=True,
        readonly=True,
        tracking=True,
    )
    in_latitude = fields.Float(
        string="Latitude",
        digits=(10, 7),
        readonly=True,
        aggregator=None,
    )
    in_longitude = fields.Float(
        string="Longitude",
        digits=(10, 7),
        readonly=True,
        aggregator=None,
    )
    in_location = fields.Char(
        help="Based on GPS-Coordinates if available or on IP Address"
    )
    in_ip_address = fields.Char(
        string="IP Address",
        readonly=True,
    )
    in_browser = fields.Char(
        string="Browser",
        readonly=True,
    )
    in_mode = fields.Selection(
        selection=[
            ("kiosk", "Kiosk"),
            ("systray", "Systray"),
            ("manual", "Manual"),
            ("technical", "Technical"),
        ],
        string="Mode",
        default="manual",
        readonly=True,
    )
    out_latitude = fields.Float(
        digits=(10, 7),
        readonly=True,
        aggregator=None,
    )
    out_longitude = fields.Float(
        digits=(10, 7),
        readonly=True,
        aggregator=None,
    )
    out_location = fields.Char(
        help="Based on GPS-Coordinates if available or on IP Address"
    )
    out_ip_address = fields.Char(readonly=True)
    out_browser = fields.Char(readonly=True)
    out_mode = fields.Selection(
        selection=[
            ("kiosk", "Kiosk"),
            ("systray", "Systray"),
            ("manual", "Manual"),
            ("technical", "Technical"),
            ("auto_check_out", "Automatic Check-Out"),
        ],
        default="manual",
        readonly=True,
    )
    expected_hours = fields.Float(
        compute="_compute_expected_hours",
        store=True,
        aggregator="sum",
    )
    device_tracking_enabled = fields.Boolean(
        related="employee_id.company_id.attendance_device_tracking"
    )
    linked_overtime_ids = fields.One2many(
        comodel_name="hr.attendance.overtime.line",
        inverse_name="attendance_id",
        readonly=False,
    )

    @api.depends("check_in", "employee_id")
    def _compute_date(self):
        for attendance in self:
            if not attendance.employee_id or not attendance.check_in:
                # A placeholder for a half-built record; `date` is a Date, so it
                # takes a date, not a datetime that only coerces on flush.
                attendance.date = fields.Date.context_today(attendance)
                continue
            tz = attendance._schedule_tz()
            attendance.date = (
                attendance.check_in.replace(tzinfo=UTC).astimezone(tz).date()
            )
            dbg.logic.debug(
                "_compute_date %s: check_in %s in %s -> %s",
                dbg.rec(attendance),
                attendance.check_in,
                tz,
                attendance.date,
            )

    @api.depends("worked_hours", "linked_overtime_ids.duration")
    def _compute_expected_hours(self):
        """Of the hours worked, the ones that were not extra.

        Against `duration`, the figure the rules computed, and not against
        `overtime_hours`, which sums `manual_duration` -- the column a manager
        edits. Correcting an overtime line used to change how many hours the
        employee had been expected to work: a twelve-hour day against an
        eight-hour schedule read 8 expected, then 11 when a manager cut the
        overtime to one hour, then 12 when they cut it to nothing, while the
        schedule never moved.
        """
        for attendance in self:
            attendance.expected_hours = attendance.worked_hours - sum(
                attendance.linked_overtime_ids.mapped("duration")
            )

    @api.depends("check_in", "check_out", "worked_hours", "out_mode")
    def _compute_color(self):
        stale = fields.Datetime.now() - timedelta(days=1)
        for attendance in self:
            if attendance.check_out:
                attendance.color = (
                    1
                    if attendance.worked_hours > 16
                    or attendance.out_mode == "technical"
                    else 0
                )
            elif not attendance.check_in:
                attendance.color = 0
            else:
                attendance.color = 1 if attendance.check_in < stale else 10

    @api.depends("linked_overtime_ids.status")
    def _compute_overtime_status(self):
        for attendance in self:
            statuses = set(attendance.linked_overtime_ids.mapped("status"))
            if not statuses:
                attendance.overtime_status = False
            elif statuses == {"approved"}:
                attendance.overtime_status = "approved"
            elif statuses == {"refused"}:
                attendance.overtime_status = "refused"
            else:
                attendance.overtime_status = "to_approve"

    @api.depends("linked_overtime_ids.manual_duration")
    def _compute_overtime_hours(self):
        for attendance in self:
            attendance.overtime_hours = sum(
                attendance.linked_overtime_ids.mapped("manual_duration")
            )

    @api.depends("linked_overtime_ids.manual_duration", "linked_overtime_ids.status")
    def _compute_validated_overtime_hours(self):
        for attendance in self:
            attendance.validated_overtime_hours = sum(
                attendance.linked_overtime_ids.filtered_domain(
                    [("status", "=", "approved")]
                ).mapped("manual_duration")
            )

    @api.depends("employee_id", "check_in", "check_out")
    def _compute_display_name(self):
        tz = request.httprequest.cookies.get("tz") if request else None
        for attendance in self:
            if not attendance.check_out:
                attendance.display_name = _(
                    "From %s",
                    format_time(
                        self.env,
                        attendance.check_in,
                        time_format=None,
                        tz=tz,
                        lang_code=self.env.lang,
                    ),
                )
            else:
                attendance.display_name = _(
                    "%(worked_hours)s (%(check_in)s-%(check_out)s)",
                    worked_hours=format_duration(attendance.worked_hours),
                    check_in=format_time(
                        self.env,
                        attendance.check_in,
                        time_format=None,
                        tz=tz,
                        lang_code=self.env.lang,
                    ),
                    check_out=format_time(
                        self.env,
                        attendance.check_out,
                        time_format=None,
                        tz=tz,
                        lang_code=self.env.lang,
                    ),
                )

    @api.depends("employee_id")
    def _compute_is_manager(self):
        have_manager_right = self.env.user.has_group(
            "hr_attendance.group_hr_attendance_user"
        )
        have_officer_right = self.env.user.has_group(
            "hr_attendance.group_hr_attendance_officer"
        )
        for attendance in self:
            attendance.is_manager = have_manager_right or (
                have_officer_right
                and attendance.attendance_manager_id.id == self.env.user.id
            )

    # A zone offset is less than a day, so the fixed point below settles in one
    # step. The bound is there because a fixed point without one is a loop.
    _SCHEDULE_VERSION_PASSES = 3

    def _schedule_version(self):
        """The employee's version in force on the LOCAL day of this check-in.

        An attendance is priced and dated by the schedule the employee was on
        when they worked it. Reading their *current* schedule instead re-dates
        and re-prices every day they have ever worked the moment they move to
        another one -- and does so silently, because the stored `date` only
        changes the next time something happens to retrigger its compute.

        Which day that is, is circular: the local day needs the zone and the
        zone comes from the version. Resolved as a fixed point rather than
        broken in favour of UTC -- pick by the UTC date, localise in that
        version's zone, re-pick by the local day, stop when it stops moving.
        Broken in favour of UTC it picked the wrong side of a schedule change:
        an attendance at 2026-09-07 22:00 UTC is already 2026-09-08 in Tokyo,
        so an employee whose new schedule starts on the 8th was priced against
        the old one for a day they worked entirely under the new.

        Where no fixed point exists -- two versions whose zones each push the
        day onto the other -- it stops on the last and does not oscillate.
        """
        self.check_singleton()
        employee = self.employee_id.sudo()
        version = employee._get_version(self.check_in.date())
        for _pass in range(self._SCHEDULE_VERSION_PASSES):
            local_day = (
                self.check_in.replace(tzinfo=UTC)
                .astimezone(timezone(version._get_schedule_tz()))
                .date()
            )
            settled = employee._get_version(local_day)
            if settled == version:
                break
            version = settled
        return version

    def _schedule_tz(self, version=None):
        """The zone that version's schedule is written in.

        Every reader of one attendance has to agree on which zone it is: the
        day `date` files it under, the lunch break `worked_hours` deducts, the
        local span the overtime engine dates its lines by. Three sources were
        in use -- the employee's current schedule, the resource's own zone and
        the version's -- and they disagree for anyone whose personal zone or
        schedule is not the one their work contact carries.
        """
        return timezone((version or self._schedule_version())._get_schedule_tz())

    def _get_employee_calendar(self, version=None):
        self.check_singleton()
        return (
            version or self._schedule_version()
        ).resource_calendar_id or self.employee_id.company_id.resource_calendar_id

    @api.depends("check_in", "check_out", "employee_id")
    def _compute_worked_hours(self):
        for attendance in self:
            if attendance.check_out and attendance.check_in and attendance.employee_id:
                attendance.worked_hours = attendance._get_worked_hours_in_range(
                    attendance.check_in, attendance.check_out
                )
            else:
                attendance.worked_hours = False

    def _get_worked_hours_in_range(self, start_dt, end_dt):
        self.check_singleton()
        return self._worked_hours_between(
            max(self.check_in, start_dt), min(self.check_out, end_dt)
        )

    def _worked_hours_between(self, start_dt, end_dt):
        """Working hours this employee's schedule places in a naive-UTC span.

        Independent of `check_out`, so it can price a span for an attendance
        that is still open -- which is what the auto-check-out cron needs to
        find where the day's hours run out, without first writing a throwaway
        check-out that would regenerate overtime and could overlap a later
        attendance.
        """
        self.check_singleton()
        # Resolved once and handed down. Reading it is a fixed point over the
        # employee's versions, and this path used to ask for it four times for
        # one span -- once here and three more inside `_lunch_intervals`.
        version = self._schedule_version()
        tz = self._schedule_tz(version)
        start_dt_tz = start_dt.replace(tzinfo=UTC).astimezone(tz)
        end_dt_tz = end_dt.replace(tzinfo=UTC).astimezone(tz)

        if end_dt_tz < start_dt_tz:
            return 0.0

        return get_intervals_hours(
            Intervals([(start_dt_tz, end_dt_tz, self)])
            - self._lunch_intervals(start_dt_tz, end_dt_tz, version=version)
        )

    def _lunch_intervals(self, start_dt_tz, end_dt_tz, version=None):
        """The schedule's lunch breaks inside a span, placed in the SCHEDULE's zone.

        `hr.employee._get_attendance_intervals` places them in the RESOURCE's
        zone, which follows the employee's work contact rather than the
        schedule they work to. When the two differ the break lands hours away
        from the span and is deducted from nothing: a nine-hour presence
        against a schedule carrying an hour of lunch was credited as nine
        worked hours instead of eight.

        Asked WITHOUT a resource, so the answer is the calendar's own lunch
        lines in the given zone and nothing else. Keyed by a resource it is not
        that: for a flexible resource the batch answers with the whole span --
        that resource may work at any time -- and subtracting it leaves no
        worked hours at all.
        """
        self.check_singleton()
        if self.employee_id.resource_id._is_flexible():
            # A flexible resource keeps no scheduled break, which is the guard
            # `hr.employee._get_attendance_intervals` was called behind.
            return Intervals([])
        version = version or self._schedule_version()
        calendar = self._get_employee_calendar(version)
        if not calendar:
            # Not a second guard on the same case: removing it fails no test,
            # and no construction reached it -- `_is_flexible()` above fires
            # first every time, because emptying the version's calendar empties
            # the resource's with it. It is here because
            # `_attendance_intervals_batch` raises ValueError on an empty
            # calendar rather than returning nothing, so should the two ever
            # diverge this answers instead of crashing.
            return Intervals([])
        return calendar._attendance_intervals_batch(
            start_dt_tz,
            end_dt_tz,
            tz=self._schedule_tz(version),
            lunch=True,
        )[False]

    @api.constrains("check_in", "check_out")
    def _check_validity_check_in_check_out(self):
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                if attendance.check_out < attendance.check_in:
                    raise exceptions.ValidationError(
                        _('"Check Out" time cannot be earlier than "Check In" time.')
                    )

    @api.constrains("check_in", "check_out", "employee_id")
    def _check_validity(self):
        """No employee may be in two places at once.

        An attendance occupies [check_in, check_out); one that has not been
        checked out yet occupies [check_in, infinity), because the employee is
        still there. Treating an open attendance as a point rather than an
        open-ended span is what used to let a completed attendance be created
        around one -- an impossible state that only surfaced later, when
        closing the open one produced an overlap nothing had checked.
        """
        for employee, attendances in self.grouped("employee_id").items():
            for earlier, later in self._sorted_span_pairs(employee, attendances):
                if earlier.check_out and earlier.check_out <= later.check_in:
                    continue
                dbg.logic.debug(
                    "_check_validity: %s overlaps %s for %s",
                    dbg.rec(earlier),
                    dbg.rec(later),
                    dbg.rec(employee),
                )
                raise exceptions.ValidationError(
                    _(
                        "Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s",
                        empl_name=employee.sudo().name,
                        datetime=format_datetime(
                            self.env, earlier.check_in, dt_format=False
                        ),
                    )
                )

    def _sorted_span_pairs(self, employee, attendances):
        """Consecutive pairs of the employee's attendances around `attendances`.

        One query per employee rather than the three per record the pairwise
        form needed, and it compares the records being checked against each
        other as well -- a batch that overlaps within itself never reached the
        database in the pairwise form.
        """
        window_start = min(attendances.mapped("check_in"))
        domain = Domain("employee_id", "=", employee.id) & Domain(
            Domain("check_out", "=", False) | Domain("check_out", ">", window_start)
        )
        if all(attendance.check_out for attendance in attendances):
            # Every checked attendance is closed, so nothing starting after the
            # last of them can reach back into one. An open attendance among
            # them has no end, so no upper bound applies.
            domain &= Domain("check_in", "<", max(attendances.mapped("check_out")))
        neighbours = self.env["hr.attendance"].sudo().search(domain)
        spans = (neighbours | attendances).sorted(lambda a: (a.check_in, a.id))
        return pairwise(spans)

    @api.model
    def _get_day_start_and_day(self, employee, dt):
        if not dt.tzinfo:
            calendar_tz = employee._get_schedule_tz_batch(dt)[employee.id]
            date_employee_tz = dt.replace(tzinfo=UTC).astimezone(timezone(calendar_tz))
        else:
            date_employee_tz = dt
        start_day_employee_tz = date_employee_tz.replace(hour=0, minute=0, second=0)
        return (
            start_day_employee_tz.astimezone(UTC).replace(tzinfo=None),
            start_day_employee_tz.date(),
        )

    def _local_date_span(self):
        self.check_singleton()
        start, stop = self._get_localized_times()
        return start.date(), stop.date()

    @staticmethod
    def _merge_windows(*window_dicts):
        merged = {}
        for windows in window_dicts:
            for employee, (first, last) in (windows or {}).items():
                if employee in merged:
                    first = min(first, merged[employee][0])
                    last = max(last, merged[employee][1])
                merged[employee] = (first, last)
        return merged

    def _overtime_windows(self):
        """{employee: (first_date, last_date)} the overtime lines of `self`
        depend on, in each employee's own calendar days.

        A quantity rule sums a whole day, or a whole week, so every attendance
        sharing that period with one of `self` has to be regenerated with it.
        Rounding to the week is paid only where a weekly rule exists: it is
        what deletes and recreates the neighbouring lines, with whatever a
        manager had approved or corrected on them.
        """
        windows = {}
        for employee, attendances in self.grouped("employee_id").items():
            spans = [
                attendance._local_date_span()
                for attendance in attendances
                if attendance.check_out
            ]
            if not spans:
                continue
            first = min(span[0] for span in spans)
            last = max(span[1] for span in spans)
            windows[employee] = employee._round_overtime_window(first, last)
            dbg.pipeline.debug(
                "[overtime:%s] window %s..%s rounded to %s..%s",
                employee.id,
                first,
                last,
                *windows[employee],
            )
        return windows

    def _attendances_in_overtime_windows(self, windows):
        """Close `windows` under "shares a day or week with", and return them
        with every attendance they cover.

        `date` is not the bound: an attendance is dated by its local check-in,
        and the day it ends on can be the next one. The prefilter is wide and
        in UTC, the exact test is on the localized span.
        """
        Attendance = self.env["hr.attendance"].sudo()
        selected = Attendance
        closed = {}
        for employee, (first, last) in windows.items():
            passes = 0
            while True:
                passes += 1
                candidates = Attendance.search(  # noqa: E8507 - walks each employee's window in pages
                    [
                        ("employee_id", "=", employee.id),
                        ("check_out", "!=", False),
                        (
                            "check_in",
                            "<=",
                            datetime.combine(last, time.max) + timedelta(days=1),
                        ),
                        (
                            "check_out",
                            ">=",
                            datetime.combine(first, time.min) - timedelta(days=1),
                        ),
                    ]
                )
                spans = [
                    span
                    for attendance in candidates
                    if (span := attendance._local_date_span())[1] >= first
                    and span[0] <= last
                ]
                if not spans:
                    break
                grown = employee._round_overtime_window(
                    min(first, *(span[0] for span in spans)),
                    max(last, *(span[1] for span in spans)),
                )
                if grown == (first, last):
                    break
                dbg.logic.debug(
                    "[overtime:%s] window grew %s..%s -> %s..%s on pass %d",
                    employee.id,
                    first,
                    last,
                    *grown,
                    passes,
                )
                first, last = grown
            closed[employee] = (first, last)
            dbg.pipeline.debug(
                "[overtime:%s] closed window %s..%s over %d attendance(s) in %d pass(es)",
                employee.id,
                first,
                last,
                len(candidates),
                passes,
            )
            selected |= candidates.filtered(
                lambda a, first=first, last=last: (
                    (span := a._local_date_span())[1] >= first and span[0] <= last
                )
            )
        return closed, selected

    def _update_overtime(self, windows=None):
        """Regenerate the overtime lines of `self`'s periods, plus `windows`.

        `windows` carries periods `self` no longer describes -- the day an
        attendance was moved away from, or the one a deleted attendance stood
        on -- in the shape `_overtime_windows` returns.
        """
        windows = self._merge_windows(self._overtime_windows(), windows)
        if not windows:
            dbg.logic.debug(
                "_update_overtime %s: no closed attendance to price", dbg.rec(self)
            )
            return
        windows, all_attendances = self._attendances_in_overtime_windows(windows)
        Line = self.env["hr.attendance.overtime.line"].sudo()
        superseded = Line.search(
            Domain.OR(
                Domain("employee_id", "=", employee.id)
                & Domain("date", ">=", first)
                & Domain("date", "<=", last)
                for employee, (first, last) in windows.items()
            )
        )
        # A manager's approval or manual correction survives a regeneration
        # that leaves the line otherwise identical -- same attendance, day,
        # rules and computed amount. Regeneration is a system act, never a
        # request to reset a human decision; only a real change to the overtime
        # (a moved shift, an edited rule) drops the line back to its default.
        decisions_by_key = defaultdict(list)
        for line in superseded:
            decisions_by_key[line._regeneration_key()].append(
                {"status": line.status, "manual_duration": line.manual_duration}
            )
        dbg.lifecycle.debug(
            "_update_overtime: dropping %d superseded line(s) over %d employee window(s)",
            len(superseded),
            len(windows),
        )
        superseded.unlink()
        if not all_attendances:
            return

        start_check_in = min(all_attendances.mapped("check_in")).date() - relativedelta(
            days=1
        )
        min_check_in = datetime.combine(start_check_in, datetime.min.time()).replace(
            tzinfo=UTC
        )

        start_check_out = max(
            all_attendances.mapped("check_out")
        ).date() + relativedelta(days=1)
        max_check_out = datetime.combine(start_check_out, datetime.max.time()).replace(
            tzinfo=UTC
        )

        version_periods_by_employee = (
            all_attendances.employee_id.sudo()._get_version_periods(
                min_check_in, max_check_out
            )
        )
        attendances_by_employee = all_attendances.grouped("employee_id")
        attendances_by_ruleset = defaultdict(lambda: self.env["hr.attendance"])
        for employee, emp_attendance in attendances_by_employee.items():
            for attendance in emp_attendance:
                attendance_intervals = Intervals(
                    [
                        (
                            attendance.check_in.replace(tzinfo=UTC),
                            attendance.check_out.replace(tzinfo=UTC),
                            self.env["hr.version"],
                        )
                    ]
                )
                inter = (
                    Intervals(version_periods_by_employee[employee])
                    & attendance_intervals
                )
                if not inter:
                    continue
                version = inter._items[0][2]
                ruleset = version.ruleset_id
                if ruleset:
                    attendances_by_ruleset[ruleset] += attendance
        employees = all_attendances.employee_id
        schedules_intervals_by_employee = (
            employees._get_schedules_by_employee_by_work_type(
                min_check_in, max_check_out, version_periods_by_employee
            )
        )
        overtime_vals_list = []
        for ruleset, ruleset_attendances in attendances_by_ruleset.items():
            attendances_dates = list(chain(*ruleset_attendances._get_dates().values()))
            overtime_vals_list.extend(
                ruleset.rule_ids._generate_overtime_vals(
                    min(attendances_dates),
                    max(attendances_dates),
                    ruleset_attendances,
                    schedules_intervals_by_employee,
                )
            )
        for vals in overtime_vals_list:
            decisions = decisions_by_key.get(Line._regeneration_key_from_vals(vals))
            if decisions:
                vals.update(decisions.pop(0))
        dbg.lifecycle.debug(
            "_update_overtime: creating %d line(s) for %d attendance(s), %d kept decision(s)",
            len(overtime_vals_list),
            len(all_attendances),
            sum(len(decisions) for decisions in decisions_by_key.values()),
        )
        # Each val carries its `attendance_id`; creating the lines marks the
        # attendance's stored `linked_overtime_ids` computes dirty through the
        # real relation, so nothing has to be marked by hand.
        Line.create(overtime_vals_list)

    _OVERTIME_SOURCE_FIELDS = frozenset({"employee_id", "check_in", "check_out"})
    _OVERTIME_DEFERRAL = "hr_attendance_deferred_overtime"

    @contextmanager
    def _deferring_overtime(self):
        """Change several attendances, then price their periods once.

        Every create, write and unlink regenerates the overtime of the whole
        period the attendance lands in -- a day, or a week where a weekly rule
        exists -- so a loop over twenty attendances pays for twenty
        regenerations of periods that mostly overlap. Inside this block those
        operations only record which periods they disturbed, and the block
        prices all of them together on the way out.

        It is not only cheaper. A regeneration deletes and recreates every line
        of the period, so the second write of a loop runs against lines the
        first one has just written and the manager decisions carried across
        them are re-matched once per pass rather than once.

        ONLY where nothing inside the block reads what the regeneration
        produces. `overtime_hours`, `validated_overtime_hours`,
        `overtime_status` and `linked_overtime_ids` are all that output, and
        inside the block they hold whatever they held before it. The absence
        cron cannot use this for exactly that reason: it drops a marker whose
        `overtime_hours` came out zero, and deferred they are all zero.

        Yields the recordset to work through: the operations that participate
        are the ones reached from it, because the deferral travels in the
        context.
        """
        pending = self.env.context.get(self._OVERTIME_DEFERRAL)
        if pending is not None:
            # Already inside a block; the outer one flushes.
            yield self
            return
        pending = {"windows": {}, "records": self.browse()}
        try:
            yield self.with_context(**{self._OVERTIME_DEFERRAL: pending})
        finally:
            # `exists()` because a record created and then deleted inside the
            # block leaves its id here; its period is still in `windows`.
            pending["records"].exists()._update_overtime(pending["windows"])

    def _defer_overtime(self, windows=None, records=None):
        """Record a disturbed period for the enclosing block, if there is one."""
        pending = self.env.context.get(self._OVERTIME_DEFERRAL)
        if pending is None:
            return False
        pending["windows"] = self._merge_windows(pending["windows"], windows)
        if records is not None:
            pending["records"] |= records
        return True

    @api.model_create_multi
    @dbg.timed
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "hr.attendance.create: %d record(s), keys %s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        res = super().create(vals_list)
        if not res._defer_overtime(records=res):
            res._update_overtime()
        return res

    def write(self, vals):
        if (
            vals.get("employee_id")
            and vals["employee_id"] not in self.env.user.employee_ids.ids
            and not self.env.user.has_group("hr_attendance.group_hr_attendance_user")
            and self.env["hr.employee"]
            .sudo()
            .browse(vals["employee_id"])
            .attendance_manager_id.id
            != self.env.user.id
        ):
            raise AccessError(
                _(
                    "Do not have access, user cannot edit the attendances that are not their own or if they are not the attendance manager of the employee."
                )
            )
        if self._OVERTIME_SOURCE_FIELDS.isdisjoint(vals):
            dbg.lifecycle.debug(
                "hr.attendance.write %s: keys %s touch no overtime source",
                dbg.rec(self),
                dbg.keys(vals),
            )
            return super().write(vals)
        dbg.lifecycle.debug(
            "hr.attendance.write %s: keys %s regenerate overtime",
            dbg.rec(self),
            dbg.keys(vals),
        )
        windows_before = self._overtime_windows()
        if self._defer_overtime(windows=windows_before, records=self):
            return super().write(vals)
        result = super().write(vals)
        self._update_overtime(windows_before)
        return result

    @dbg.timed
    def unlink(self):
        dbg.lifecycle.debug("hr.attendance.unlink %s", dbg.rec(self))
        windows = self._overtime_windows()
        # Unlink the lines through the ORM rather than leaving the database's
        # `ondelete=cascade` to drop them: a cascade at the SQL level removes
        # the rows without the ORM noticing, so the employee's non-stored
        # `total_overtime` keeps its pre-delete value in cache. The cascade
        # stays as an integrity net for any path that does not come through here.
        self.linked_overtime_ids.unlink()
        # Only the windows: the records are about to stop existing, so there is
        # nothing left to price them from.
        deferred = self._defer_overtime(windows=windows)
        res = super().unlink()
        if not deferred:
            self.env["hr.attendance"]._update_overtime(windows)
        return res

    def copy(self, default=None):
        raise exceptions.UserError(_("You cannot duplicate an attendance."))

    def _action_attendance_maps(self, side):
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "url": get_google_maps_url(
                self[f"{side}_latitude"], self[f"{side}_longitude"]
            ),
            "target": "new",
        }

    def action_in_attendance_maps(self):
        return self._action_attendance_maps("in")

    def action_out_attendance_maps(self):
        return self._action_attendance_maps("out")

    def get_kiosk_url(self):
        return (
            self.get_base_url()
            + "/hr_attendance/"
            + self.env.company.attendance_kiosk_key
        )

    @api.model
    def has_demo_data(self):
        if not self.env.user.has_group("hr_attendance.group_hr_attendance_user"):
            return True
        demo_tag = self.env.ref(
            "hr_attendance.resource_calendar_std_38h", raise_if_not_found=False
        )
        return bool(demo_tag) or bool(
            self.env["ir.module.module"].search_count([("demo", "=", True)], limit=1)
        )

    def _load_demo_data(self):
        if self.has_demo_data():
            dbg.logic.debug("_load_demo_data: database already carries sample data")
            return None
        env_sudo = self.sudo().with_context({}).env
        env_sudo["hr.employee"]._load_scenario()
        convert.convert_file(
            env_sudo,
            "hr_attendance",
            "data/scenarios/hr_attendance_scenario.xml",
            None,
            mode="init",
        )
        self.env["hr.attendance"].create(demo.attendance_vals(env_sudo))
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_try_kiosk(self):
        if not self.env.user.has_group("hr_attendance.group_hr_attendance_user"):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "message": _("You don't have the rights to execute that action."),
                    "type": "info",
                },
            }
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": self.env.company.attendance_kiosk_url + "?from_trial_mode=True",
        }

    def _read_group_employee_id(self, resources, domain):
        user_domain = Domain(self.env.context.get("user_domain") or Domain.TRUE)
        employee_domain = Domain(
            "company_id", "in", self.env.context.get("allowed_company_ids", [])
        )
        if not self.env.user.has_group("hr_attendance.group_hr_attendance_user"):
            employee_domain &= Domain("attendance_manager_id", "=", self.env.user.id)
        if user_domain.is_true():
            if "gantt_start_date" in self.env.context:
                return self.env["hr.employee"].search(employee_domain)
            return resources & self.env["hr.employee"].search(employee_domain)
        else:
            employee_name_domain = Domain.OR(
                Domain("name", condition.operator, condition.value)
                for condition in user_domain.iter_conditions()
                if condition.field_expr == "employee_id"
            )
            return resources | self.env["hr.employee"].search(
                employee_name_domain & employee_domain
            )

    def _linked_overtimes(self):
        return self.linked_overtime_ids

    def action_approve_overtime(self):
        self.linked_overtime_ids.action_approve()

    def action_refuse_overtime(self):
        self.linked_overtime_ids.action_refuse()

    def _local_check_in(self):
        self.check_singleton()
        return self.check_in.replace(tzinfo=UTC).astimezone(self._schedule_tz())

    def _scheduled_hours_on(self, local_day):
        """Worked hours the schedule places on one of the employee's own days.

        The calendar's own batch rather than a hand-rolled sweep of
        `attendance_ids`: that sweep summed every line matching the weekday,
        the lunch line included, so a 9-17 schedule with an hour's lunch
        claimed eight expected *worked* hours where the employee works seven --
        and it re-derived the two-week alternation the batch already knows.
        """
        self.check_singleton()
        calendar = self._get_employee_calendar()
        if not calendar:
            return 0.0
        tz = self._schedule_tz()
        # Without a resource, for the same reason as `_lunch_intervals`: keyed
        # by a flexible resource the batch answers with the whole day.
        #
        # Bounded by the NEXT local midnight rather than by `time.max`, so the
        # window tiles the day by construction. A local day is not always 24
        # hours: where the clocks go back at midnight it has 25, its last hour
        # repeats, and `time.max` resolves to the first of the two. Measured
        # over twelve zones and every day of 2026, the closed form leaves
        # 3600s uncovered on America/Santiago 2026-04-04 and Asia/Beirut
        # 2026-10-24; the half-open form leaves nothing anywhere.
        #
        # It changes no figure TODAY: `_attendance_intervals_batch` walks
        # `rrule(DAILY, ...)` and materialises each calendar line once per
        # calendar day, so it does not model the repeated hour either way --
        # measured 0.983h from both windows for a 23:00-23:59 shift on that
        # Santiago day. The bound is here so that a consumer which does model
        # it is not handed a window an hour short.
        return get_intervals_hours(
            calendar._attendance_intervals_batch(
                datetime.combine(local_day, time.min).replace(tzinfo=tz),
                datetime.combine(local_day + timedelta(days=1), time.min).replace(
                    tzinfo=tz
                ),
                tz=tz,
            )[False]
        )

    # A shift long enough to need more than a week of the schedule to spend its
    # budget is a data error, not a shift; stop walking rather than loop.
    _AUTO_CHECK_OUT_HORIZON_DAYS = 7

    def _worked_hours_spent_at(self, budget):
        """When `budget` worked hours have accrued since check-in.

        Walked rather than added, because the answer is not `check_in + budget`:
        a break inside the span pushes it later. And walked past local midnight,
        because a shift that starts in the evening spends its budget on the next
        calendar day -- which is the case the previous form got wrong twice
        over. It anchored on `check_in.replace(hour=23, minute=59, second=59)`,
        the end of the check-in's UTC day rather than the employee's, and then
        subtracted the excess from that anchor, which is exact only when no
        break falls inside the part subtracted.
        """
        self.check_singleton()
        tz = self._schedule_tz()
        cursor = self._local_check_in()
        floor = self.check_in + timedelta(seconds=1)
        spent = 0.0
        for _day in range(self._AUTO_CHECK_OUT_HORIZON_DAYS):
            # The next local midnight, not `time.max`: a day that ends a
            # microsecond early leaves that microsecond of the budget to be
            # spent on the following day, and the cut lands a microsecond late.
            day_end = datetime.combine(
                cursor.date() + timedelta(days=1), time.min
            ).replace(tzinfo=tz)
            for period_start, period_stop, _record in Intervals(
                [(cursor, day_end, self)]
            ) - self._lunch_intervals(cursor, day_end):
                hours = (period_stop - period_start).total_seconds() / 3600
                if spent + hours >= budget:
                    reached = period_start + timedelta(hours=budget - spent)
                    return max(reached.astimezone(UTC).replace(tzinfo=None), floor)
                spent += hours
            cursor = day_end.astimezone(tz)
        return max(cursor.astimezone(UTC).replace(tzinfo=None), floor)

    def _worked_hours_already_closed(self):
        """{employee_id: {local day: worked hours}} for what `self`'s employees
        have already closed on the days `self` start on.

        Bounded a day wider than the earliest check-in: an attendance that
        opened before local midnight belongs to the same local day as one that
        opened after it, and the previous bound was a naive-UTC midnight that
        dropped it for anyone far enough east.
        """
        totals = defaultdict(lambda: defaultdict(float))
        if not self:
            return totals
        earliest = min(self.mapped("check_in")).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
        closed = self.env["hr.attendance"].search(
            [
                ("employee_id", "in", self.employee_id.ids),
                ("check_in", ">=", earliest),
                ("check_out", "!=", False),
            ]
        )
        for attendance in closed:
            totals[attendance.employee_id.id][attendance._local_check_in().date()] += (
                attendance.worked_hours
            )
        return totals

    @dbg.timed
    def _cron_auto_check_out(self):
        """Close the attendances of employees who have not checked out.

        Everything here is counted in *worked* hours -- what the employee is
        credited with and what their overtime is measured from. The four
        quantities used to be three different currencies: wall-clock presence
        for the open attendance, worked hours for the earlier ones, and
        scheduled presence including lunch for what was expected, so the same
        day could be over budget by an hour of lunch nobody worked.
        """
        to_verify = self.env["hr.attendance"].search(
            [
                ("check_out", "=", False),
                ("employee_id.company_id.auto_check_out", "=", True),
                ("employee_id.resource_calendar_id.flexible_hours", "=", False),
            ]
        )

        dbg.lifecycle.debug(
            "_cron_auto_check_out: %d open attendance(s) to verify", len(to_verify)
        )
        if not to_verify:
            return

        now = fields.Datetime.now()
        already_closed = to_verify._worked_hours_already_closed()
        closed = self.browse()
        # One block for the whole sweep: each `write` below would otherwise
        # regenerate the overtime of the day it lands in, and the employees a
        # sweep closes together largely share their days.
        with to_verify._deferring_overtime() as attendances:
            for attendance in attendances:
                employee = attendance.employee_id
                local_day = attendance._local_check_in().date()
                budget = (
                    attendance._scheduled_hours_on(local_day)
                    + employee.company_id.auto_check_out_tolerance
                    - already_closed[employee.id][local_day]
                )
                worked = attendance._worked_hours_between(attendance.check_in, now)
                dbg.logic.debug(
                    "_cron_auto_check_out %s: %.3fh worked against a %.3fh budget"
                    " on %s (%s)",
                    dbg.rec(attendance),
                    worked,
                    budget,
                    local_day,
                    attendance._schedule_tz(),
                )
                if worked <= budget:
                    continue
                check_out = attendance._worked_hours_spent_at(budget)
                dbg.lifecycle.debug(
                    "_cron_auto_check_out %s: closing at %s",
                    dbg.rec(attendance),
                    check_out,
                )
                attendance.write({"check_out": check_out, "out_mode": "auto_check_out"})
                closed |= attendance
        closed._log_cron_note(
            _(
                "This attendance was automatically checked out because the employee exceeded the allowed time for their scheduled work hours."
            )
        )

    def _log_cron_note(self, body):
        """One chatter entry per attendance, written in one batch.

        `message_post` per record costs a round of queries for each of them and
        these are sweeps. Measured field by field, the two write the same
        message -- same author, body, `message_type` and Note subtype, nobody
        notified -- with one exception: `_message_log_batch` marks it
        `is_internal`, which `message_post` leaves False. `hr.attendance` has
        no portal surface for that flag to change anything on, but the flag is
        restored anyway rather than left as an undocumented difference between
        a note written by the cron and one written anywhere else.
        """
        if not self:
            return
        self._message_log_batch(dict.fromkeys(self.ids, body)).is_internal = False

    @dbg.timed
    def _cron_absence_detection(self):
        yesterday = fields.Date.today() - relativedelta(days=1)
        companies = self.env["res.company"].search([("absence_management", "=", True)])
        dbg.lifecycle.debug(
            "_cron_absence_detection: %s, %d company/companies manage absence",
            yesterday,
            len(companies),
        )
        if not companies:
            return

        # Both scans are bounded by the companies that asked for absence
        # management. Unbounded, the second one reads every attendance ever
        # left open in the database -- in every company, back to the first one
        # anybody forgot to close -- to answer a question about a handful of
        # employees.
        in_scope = Domain("employee_id.company_id", "in", companies.ids)
        # An employee who worked exactly their expected hours has no overtime
        # line for the day; the attendances are what say they were there.
        checked_in_employees = (
            self.env["hr.attendance"]
            .search(in_scope & Domain("date", "=", yesterday))
            .employee_id
        )
        # An employee who never checked out is not absent -- they are recorded
        # as still being there. Marking them absent contradicts their own open
        # attendance, and the marker cannot be placed without overlapping it.
        still_checked_in = (
            self.env["hr.attendance"]
            .search(in_scope & Domain("check_out", "=", False))
            .employee_id
        )

        technical_attendances_vals = []
        absent_employees = self.env["hr.employee"].search(
            [
                ("id", "not in", (checked_in_employees | still_checked_in).ids),
                ("company_id", "in", companies.ids),
                ("resource_calendar_id.flexible_hours", "=", False),
                ("current_version_id.contract_date_start", "<=", yesterday),
                "|",
                ("current_version_id.contract_date_end", "=", False),
                ("current_version_id.contract_date_end", ">=", yesterday),
            ]
        )

        for emp in absent_employees:
            # Midnight of the absent day *in the employee's own time zone*,
            # expressed in UTC for storage. Converting the server's midnight
            # into the employee's zone and then storing that wall clock as UTC
            # placed the marker a whole day off for anyone far enough east.
            local_day_start = datetime.combine(yesterday, time.min).replace(
                tzinfo=timezone(emp.sudo()._get_version(yesterday)._get_schedule_tz())
            )
            check_in = local_day_start.astimezone(UTC).replace(tzinfo=None)
            technical_attendances_vals.append(
                {
                    "check_in": check_in,
                    "check_out": check_in + relativedelta(seconds=1),
                    "in_mode": "technical",
                    "out_mode": "technical",
                    "employee_id": emp.id,
                }
            )

        dbg.lifecycle.debug(
            "_cron_absence_detection: %d absent employee(s) get a technical attendance",
            len(technical_attendances_vals),
        )
        # NOT deferred, though the create and the unlink disturb the same days:
        # `overtime_hours` below is the regeneration's own output, and the whole
        # point of the filter is to drop a marker that produced none. Deferring
        # makes every marker read zero and deletes all of them.
        technical_attendances = self.create(technical_attendances_vals)
        to_unlink = technical_attendances.filtered(lambda a: a.overtime_hours == 0)
        dbg.logic.debug(
            "_cron_absence_detection: %d of %d marker(s) produced no overtime, dropping",
            len(to_unlink),
            len(technical_attendances),
        )
        kept = technical_attendances - to_unlink
        to_unlink.unlink()
        kept._log_cron_note(
            _(
                "This attendance was automatically created to cover an unjustified absence on that day."
            )
        )

    def _get_localized_times(self):
        self.check_singleton()
        tz = self._schedule_tz()
        dbg.logic.debug("_get_localized_times %s: schedule zone %s", dbg.rec(self), tz)
        localized_start = (
            self.check_in.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        )
        localized_end = (
            self.check_out.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        )
        return localized_start, localized_end

    def _get_dates(self):
        result = {}
        for attendance in self:
            localized_start, localized_end = attendance._get_localized_times()
            result[attendance] = list(
                rrule(
                    DAILY,
                    dtstart=localized_start.date(),
                    until=localized_end.date(),
                )
            )
        return result

    def _get_attendance_by_periods_by_employee(self):
        attendance_by_employee_by_day = defaultdict(
            lambda: defaultdict(lambda: Intervals([], keep_distinct=True))
        )
        attendance_by_employee_by_week = defaultdict(
            lambda: defaultdict(lambda: Intervals([], keep_distinct=True))
        )

        for attendance in self.sorted("check_in"):
            employee = attendance.employee_id
            check_in, check_out = attendance._get_localized_times()
            for day in rrule(
                dtstart=check_in.date(), until=check_out.date(), freq=DAILY
            ):
                week_date = day + relativedelta(days=6 - day.weekday())

                start_datetime = datetime.combine(day, time.min)
                stop_datetime_for_day = datetime.combine(day, time.max)
                day_interval = Intervals(
                    [
                        (
                            start_datetime,
                            stop_datetime_for_day,
                            self.env["resource.calendar"],
                        )
                    ]
                )

                stop_datetime_for_week = datetime.combine(week_date, time.max)
                week_interval = Intervals(
                    [
                        (
                            start_datetime,
                            stop_datetime_for_week,
                            self.env["resource.calendar"],
                        )
                    ]
                )

                attendance_interval = Intervals([(check_in, check_out, attendance)])
                attendance_by_employee_by_day[employee][day] |= (
                    attendance_interval & day_interval
                )
                attendance_by_employee_by_week[employee][week_date] |= (
                    attendance_interval & week_interval
                )

        return {
            "day": attendance_by_employee_by_day,
            "week": attendance_by_employee_by_week,
        }
