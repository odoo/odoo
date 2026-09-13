from calendar import monthrange
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from itertools import chain, pairwise
from random import randint

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
            tz = timezone(attendance.employee_id._get_tz())
            attendance.date = (
                attendance.check_in.replace(tzinfo=UTC).astimezone(tz).date()
            )

    @api.depends("worked_hours", "overtime_hours")
    def _compute_expected_hours(self):
        for attendance in self:
            attendance.expected_hours = (
                attendance.worked_hours - attendance.overtime_hours
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

    def _get_employee_calendar(self):
        self.check_singleton()
        return (
            self.employee_id.resource_calendar_id
            or self.employee_id.company_id.resource_calendar_id
        )

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
        calendar = self._get_employee_calendar()
        resource = self.employee_id.resource_id
        tz = timezone(resource.tz) if not calendar else timezone(calendar.tz)
        start_dt_tz = start_dt.replace(tzinfo=UTC).astimezone(tz)
        end_dt_tz = end_dt.replace(tzinfo=UTC).astimezone(tz)

        if end_dt_tz < start_dt_tz:
            return 0.0

        lunch_intervals = []
        if not resource._is_flexible():
            lunch_intervals = self.employee_id._get_attendance_intervals(
                start_dt_tz, end_dt_tz, lunch=True
            )
        attendance_intervals = (
            Intervals([(start_dt_tz, end_dt_tz, self)]) - lunch_intervals
        )
        return get_intervals_hours(attendance_intervals)

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
            calendar_tz = employee._get_calendar_tz_batch(dt)[employee.id]
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
            while True:
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
                first, last = grown
            closed[employee] = (first, last)
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
        # Each val carries its `attendance_id`; creating the lines marks the
        # attendance's stored `linked_overtime_ids` computes dirty through the
        # real relation, so nothing has to be marked by hand.
        Line.create(overtime_vals_list)

    _OVERTIME_SOURCE_FIELDS = frozenset({"employee_id", "check_in", "check_out"})

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
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
            return super().write(vals)
        windows_before = self._overtime_windows()
        result = super().write(vals)
        self._update_overtime(windows_before)
        return result

    def unlink(self):
        windows = self._overtime_windows()
        # Unlink the lines through the ORM rather than leaving the database's
        # `ondelete=cascade` to drop them: a cascade at the SQL level removes
        # the rows without the ORM noticing, so the employee's non-stored
        # `total_overtime` keeps its pre-delete value in cache. The cascade
        # stays as an integrity net for any path that does not come through here.
        self.linked_overtime_ids.unlink()
        res = super().unlink()
        self.env["hr.attendance"]._update_overtime(windows)
        return res

    def copy(self, default=None):
        raise exceptions.UserError(_("You cannot duplicate an attendance."))

    def action_in_attendance_maps(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "url": get_google_maps_url(self.in_latitude, self.in_longitude),
            "target": "new",
        }

    def action_out_attendance_maps(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_url",
            "url": get_google_maps_url(self.out_latitude, self.out_longitude),
            "target": "new",
        }

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
        self.env["hr.attendance"].create(self._demo_attendance_vals())
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def _demo_working_days(self):
        now = fields.Datetime.now()
        previous_month = now - relativedelta(months=1)
        days_back = now.day + monthrange(previous_month.year, previous_month.month)[1]
        for offset in range(1, days_back):
            morning_in = now.replace(
                hour=6, minute=0, second=randint(0, 59)
            ) + timedelta(days=-offset, minutes=randint(-2, 3))
            if morning_in.weekday() not in range(5):
                continue
            yield {
                "morning_in": morning_in,
                "morning_out": now.replace(hour=10, minute=0, second=randint(0, 59))
                + timedelta(days=-offset, minutes=randint(-2, -1)),
                "afternoon_in": now.replace(hour=11, minute=0, second=randint(0, 59))
                + timedelta(days=-offset, minutes=randint(-2, -1)),
                "afternoon_out": now.replace(hour=15, minute=0, second=randint(0, 59))
                + timedelta(days=-offset, minutes=randint(1, 3)),
            }

    @staticmethod
    def _demo_day_vals(employee, mode, morning, afternoon, **extra):
        return [
            {
                "employee_id": employee.id,
                "check_in": check_in,
                "check_out": check_out,
                "in_mode": mode,
                "out_mode": mode,
                **extra,
            }
            for check_in, check_out in (morning, afternoon)
        ]

    def _demo_kiosk_day_vals(self, employee, day):
        if day["morning_in"].weekday() == 4:
            return []
        if day["morning_in"].isocalendar().week % 2:
            morning_shift, afternoon_shift = timedelta(hours=1), timedelta(hours=-1)
        else:
            morning_shift = timedelta()
            afternoon_shift = timedelta(hours=1, minutes=30)
        return self._demo_day_vals(
            employee,
            "kiosk",
            (day["morning_in"] + morning_shift, day["morning_out"]),
            (day["afternoon_in"], day["afternoon_out"] + afternoon_shift),
        )

    def _demo_systray_day_vals(self, employee, day):
        usual = {"latitude": 51.01, "longitude": 2.82, "city": "Rellemstraat"}
        occasional = {"latitude": 50.27, "longitude": 5.31, "city": "Waillet"}
        where = occasional if randint(1, 10) == 1 else usual
        return self._demo_day_vals(
            employee,
            "systray",
            (day["morning_in"], day["morning_out"]),
            (day["afternoon_in"], day["afternoon_out"]),
            **{
                f"{side}_{key}": value
                for side in ("in", "out")
                for key, value in (
                    ("latitude", where["latitude"]),
                    ("longitude", where["longitude"]),
                    ("location", where["city"]),
                    ("ip_address", "127.0.0.1"),
                    ("browser", "chrome"),
                )
            },
        )

    def _demo_manual_day_vals(self, employee, day):
        return self._demo_day_vals(
            employee,
            "manual",
            (
                day["morning_in"] + timedelta(minutes=randint(-10, -5)),
                day["morning_out"],
            ),
            (
                day["afternoon_in"],
                day["afternoon_out"] + timedelta(hours=1, minutes=randint(-20, 10)),
            ),
        )

    def _demo_attendance_vals(self):
        by_employee = (
            (self.env.ref("hr.employee_eg"), self._demo_kiosk_day_vals),
            (self.env.ref("hr.employee_mw"), self._demo_systray_day_vals),
            (self.env.ref("hr.employee_sj"), self._demo_manual_day_vals),
        )
        return [
            vals
            for day in self._demo_working_days()
            for employee, build in by_employee
            for vals in build(employee, day)
        ]

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

    def _cron_auto_check_out(self):
        def check_in_tz(attendance):
            return attendance.check_in.replace(tzinfo=UTC).astimezone(
                timezone(attendance.employee_id._get_tz())
            )

        to_verify = self.env["hr.attendance"].search(
            [
                ("check_out", "=", False),
                ("employee_id.company_id.auto_check_out", "=", True),
                ("employee_id.resource_calendar_id.flexible_hours", "=", False),
            ]
        )

        if not to_verify:
            return

        to_verify_min_date = min(to_verify.mapped("check_in")).replace(
            hour=0, minute=0, second=0
        )
        previous_attendances = self.env["hr.attendance"].search(
            [
                ("employee_id", "in", to_verify.mapped("employee_id").ids),
                ("check_in", ">", to_verify_min_date),
                ("check_out", "!=", False),
            ]
        )

        mapped_previous_duration = defaultdict(lambda: defaultdict(float))
        for previous in previous_attendances:
            mapped_previous_duration[previous.employee_id][
                check_in_tz(previous).date()
            ] += previous.worked_hours

        all_companies = to_verify.employee_id.company_id

        for company in all_companies:
            max_tol = company.auto_check_out_tolerance
            to_verify_company = to_verify.filtered(
                lambda a, company=company: a.employee_id.company_id.id == company.id
            )

            for att in to_verify_company:
                employee_timezone = timezone(att.employee_id._get_tz())
                check_in_datetime = check_in_tz(att)
                now_datetime = (
                    fields.Datetime.now()
                    .replace(tzinfo=UTC)
                    .astimezone(employee_timezone)
                )
                current_attendance_duration = (
                    now_datetime - check_in_datetime
                ).total_seconds() / 3600
                previous_attendances_duration = mapped_previous_duration[
                    att.employee_id
                ][check_in_datetime.date()]

                expected_worked_hours = sum(
                    att.employee_id.resource_calendar_id.attendance_ids.filtered(
                        lambda a, check_in_datetime=check_in_datetime: (
                            a.dayofweek == str(check_in_datetime.weekday())
                            and (
                                not a.two_weeks_calendar
                                or a.week_type
                                == str(a.get_week_type(check_in_datetime.date()))
                            )
                        )
                    ).mapped("duration_hours")
                )

                if (
                    current_attendance_duration
                    + previous_attendances_duration
                    - max_tol
                ) > expected_worked_hours:
                    # Where the day's allowance runs out, priced without first
                    # writing a throwaway end-of-day check-out: one write and one
                    # overtime regeneration instead of two.
                    end_of_day = att.check_in.replace(hour=23, minute=59, second=59)
                    worked_to_end_of_day = att._worked_hours_between(
                        att.check_in, end_of_day
                    )
                    excess_hours = worked_to_end_of_day - (
                        expected_worked_hours + max_tol - previous_attendances_duration
                    )
                    att.write(
                        {
                            "check_out": max(
                                end_of_day - relativedelta(hours=excess_hours),
                                att.check_in + relativedelta(seconds=1),
                            ),
                            "out_mode": "auto_check_out",
                        }
                    )
                    att.message_post(
                        body=_(
                            "This attendance was automatically checked out because the employee exceeded the allowed time for their scheduled work hours."
                        )
                    )

    def _cron_absence_detection(self):
        yesterday = fields.Date.today() - relativedelta(days=1)
        companies = self.env["res.company"].search([("absence_management", "=", True)])
        if not companies:
            return

        # An employee who worked exactly their expected hours has no overtime
        # line for the day; the attendances are what say they were there.
        checked_in_employees = (
            self.env["hr.attendance"].search([("date", "=", yesterday)]).employee_id
        )
        # An employee who never checked out is not absent -- they are recorded
        # as still being there. Marking them absent contradicts their own open
        # attendance, and the marker cannot be placed without overlapping it.
        still_checked_in = (
            self.env["hr.attendance"].search([("check_out", "=", False)]).employee_id
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
                tzinfo=timezone(emp._get_tz())
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

        technical_attendances = self.env["hr.attendance"].create(
            technical_attendances_vals
        )
        to_unlink = technical_attendances.filtered(lambda a: a.overtime_hours == 0)

        body = _(
            "This attendance was automatically created to cover an unjustified absence on that day."
        )
        for technical_attendance in technical_attendances - to_unlink:
            technical_attendance.message_post(body=body)

        to_unlink.unlink()

    def _get_localized_times(self):
        self.check_singleton()
        tz = timezone(
            self.employee_id.sudo()._get_version(self.check_in.date())._get_tz()
        )
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
