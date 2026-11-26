# Part of Odoo. See LICENSE file for full copyright and licensing details.

from bisect import bisect_left, bisect_right
from calendar import monthrange
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from random import randint
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule
from markupsafe import Markup

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools import convert, float_compare, float_is_zero, format_datetime
from odoo.tools.date_utils import date_range, float_to_time, time_to_float
from odoo.tools.intervals import Intervals


def get_google_maps_url(latitude, longitude):
    return "https://maps.google.com?q=%s,%s" % (latitude, longitude)


# color index of each review state, shared by the calendar and gantt views
_STATE_COLORS = {
    'draft': 2,  # orange
    'validated': 10,  # green
    'refused': 1,  # red
}


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _description = "Attendance"
    _order = "check_in desc"
    _inherit = ["mail.thread"]

    def _default_employee(self):
        return self.env.user.employee_id

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        context = self.env.context
        # A click on a day in the calendar or gantt view (isAllDay): propose the employee's schedule of that day
        if context.get('isAllDay') and context.get('allDayDate') and res.get('employee_id') \
                and {'check_in', 'check_out'} & set(fields):
            day = datetime.fromisoformat(context['allDayDate']).date()
            employee = self.env['hr.employee'].browse(res['employee_id'])
            check_in, check_out = employee._get_default_attendance_slot(day)
            res.update({key: value for key, value in (('check_in', check_in), ('check_out', check_out)) if key in fields})
        return res

    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=True,
        ondelete='cascade', index=True)
    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id",
        readonly=True)
    manager_id = fields.Many2one(comodel_name='hr.employee', related="employee_id.parent_id", readonly=True,
        export_string_translation=False)
    attendance_manager_id = fields.Many2one('res.users', related="employee_id.attendance_manager_id",
        export_string_translation=False)
    is_manager = fields.Boolean(compute="_compute_is_manager")
    is_own = fields.Boolean(compute="_compute_is_manager")
    can_edit = fields.Boolean(compute="_compute_can_edit")
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=True, tracking=True, index=True)
    check_out = fields.Datetime(string="Check Out", tracking=True)
    date = fields.Date(string="Date", compute='_compute_date', store=True, index=True, precompute=True, required=True)
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)
    expected_hours = fields.Float(string="Expected Hours", compute='_compute_expected_hours', store=True, readonly=True,
        help="Hours of the working schedule of the check in day (time off deduced), shared by its attendances: "
             "each one expects the hours it worked, the last one of the day what remains.")
    overtime_hours = fields.Float(string="Overtime", compute='_compute_overtime_hours', store=True, readonly=True,
        help="Worked hours minus expected hours. Negative when the employee worked less than expected.")
    color = fields.Integer(compute='_compute_color', export_string_translation=False)
    in_latitude = fields.Float(string="Latitude", digits=(10, 7), readonly=True, aggregator=None)
    in_longitude = fields.Float(string="Longitude", digits=(10, 7), readonly=True, aggregator=None)
    in_location = fields.Char(help="Based on GPS-Coordinates if available or on IP Address")
    in_ip_address = fields.Char(string="IP Address", readonly=True)
    in_browser = fields.Char(string="Browser", readonly=True)
    in_mode = fields.Selection(string="Mode",
                               selection=[('kiosk', "Kiosk"),
                                          ('systray', "Systray"),
                                          ('manual', "Manual"),
                                          ('technical', 'Technical')],
                               readonly=True,
                               tracking=True,
                               default='manual')
    in_image = fields.Binary(string="Check-In Image")
    out_latitude = fields.Float(digits=(10, 7), readonly=True, aggregator=None)
    out_longitude = fields.Float(digits=(10, 7), readonly=True, aggregator=None)
    out_location = fields.Char(help="Based on GPS-Coordinates if available or on IP Address")
    out_ip_address = fields.Char(string="Out IP Address", readonly=True)
    out_browser = fields.Char(readonly=True)
    out_mode = fields.Selection(selection=[('kiosk', "Kiosk"),
                                           ('systray', "Systray"),
                                           ('manual', "Manual"),
                                           ('technical', 'Technical'),
                                           ('auto_check_out', 'Automatic Check-Out')],
                                readonly=True,
                                # empty until the check-out, so the chatter does not log a manual check-out first
                                tracking=True)
    device_tracking_enabled = fields.Boolean(related="employee_id.company_id.attendance_device_tracking")
    day_of_date = fields.Selection(
        compute='_compute_day_of_date',
        store=True,
        string="Day",
        index=True,
        selection=[('0', "Monday"), ('1', "Tuesday"), ('2', "Wednesday"), ('3', "Thursday"), ('4', "Friday"), ('5', "Saturday"), ('6', "Sunday")],
    )
    resource_calendar_id = fields.Many2one(related='employee_id.resource_calendar_id', string="Working Schedule")
    break_duration = fields.Float(string="Break Duration", tracking=True, help="Extra unpaid break duration (hours)")
    employee_tz = fields.Char(compute='_compute_employee_tz', export_string_translation=False)

    state = fields.Selection([
        ('draft', 'To Review'),
        ('validated', 'Reviewed'),
        ('refused', 'Refused'),
    ], string='Status', required=True, default='draft', index=True, tracking=True, readonly=True, copy=False)
    # issues of the employee's day, see _compute_attendance_issues
    is_late_check_in = fields.Boolean(string="Late Clock In", compute="_compute_attendance_issues", store=True)
    is_early_check_out = fields.Boolean(string="Early Clock Out", compute="_compute_attendance_issues", store=True)
    has_issue = fields.Boolean(
        compute="_compute_has_issue",
        export_string_translation=False,
        help="Late check-in, early check-out, overtime, undertime or another issue, flagged on the gantt view.",
    )

    @api.depends('date')
    def _compute_day_of_date(self):
        for record in self:
            if record.date:
                record.day_of_date = str(record.date.weekday())
            else:
                record.day_of_date = False

    @api.depends("check_in", "employee_id")
    def _compute_date(self):
        for attendance in self:
            if not attendance.employee_id or not attendance.check_in:  # weird precompute edge cases. Never after creation
                attendance.date = datetime.today()
                continue
            tz = ZoneInfo(attendance.employee_id._get_tz())
            attendance.date = attendance.check_in.replace(tzinfo=UTC).astimezone(tz).date()

    @api.depends('state')
    def _compute_color(self):
        """Color index of the review state: orange to review, green reviewed, red refused."""
        for attendance in self:
            attendance.color = _STATE_COLORS[attendance.state]

    @api.depends("worked_hours", "check_out")
    def _compute_display_name(self):
        for attendance in self:
            if not attendance.check_out:
                name = self.env._("At Work")
            else:
                hours, minutes = divmod(round(attendance.worked_hours * 60), 60)
                if minutes:
                    name = self.env._("%(hours)sh %(minutes)sm", hours=hours, minutes=minutes)
                else:
                    name = self.env._("%(hours)sh", hours=hours)
            attendance.display_name = name

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_is_manager(self):
        have_own_right = self.env.user.has_group('hr_attendance.group_hr_attendance_own')
        have_manager_right = self.env.user.has_group('hr_attendance.group_hr_attendance_user')
        managed_employees = self.employee_id._filter_attendance_managed_by_current_user()
        for attendance in self:
            # a new attendance has no employee until one is chosen
            attendance.is_manager = (
                attendance.employee_id in managed_employees if attendance.employee_id else have_manager_right
            )
            attendance.is_own = have_own_right and attendance.employee_id.user_id == self.env.user

    @api.depends('is_manager', 'is_own', 'state')
    def _compute_can_edit(self):
        for attendance in self:
            # the users may not edit their refused attendances (record rule)
            attendance.can_edit = attendance.is_manager or (attendance.is_own and attendance.state != 'refused')

    @api.depends('check_in', 'check_out', 'break_duration')
    def _compute_worked_hours(self):
        """Compute ``worked_hours``: ``check_out - check_in`` in hours, minus ``break_duration``.

        The schedule (lunch break included) is not used. Open attendances get ``0``.
        """
        for attendance in self:
            if attendance.check_out and attendance.check_in and attendance.employee_id:
                attendance.worked_hours = (
                    time_to_float(attendance.check_out - attendance.check_in)
                ) - attendance.break_duration
            else:
                attendance.worked_hours = False

    @api.depends('employee_id', 'check_in', 'check_out', 'break_duration', 'state')
    def _compute_expected_hours(self):
        """Share the expected hours of the day of the attendances (``date``, the local day of the
        check in) between them, in check in order: each one expects up to its worked hours, the
        last one what remains. Only the check in day counts: an attendance over midnight expects the
        hours of the day it starts on, whatever its length. A refused attendance did not happen: it
        expects nothing, the other attendances of the day share the day.

        The expected hours of a day are the work intervals of
        ``hr.employee._get_expected_attendances_batch`` (working schedule, time off deduced) within
        that local day. A schedule line never crosses midnight, so a timed night schedule splits each
        night between two days: night workers need a schedule by duration.
        """
        attendances, invalid = self.partitioned(lambda a: a.employee_id and a.check_in)
        for attendance in invalid:
            attendance.expected_hours = 0.0
        if not attendances:
            return
        days = {(attendance.employee_id, attendance.date) for attendance in attendances}
        same_day = attendances | (attendances._search_same_day_attendances() - attendances._origin)
        attendances_by_day = same_day.filtered(lambda a: (a.employee_id, a.date) in days).grouped(
            lambda a: (a.employee_id, a.date))
        # the expected hours of each local day, one fetch per timezone (the employee's on that day)
        hours_by_day = defaultdict(float)
        for tz_name, tz_attendances in attendances.grouped(lambda a: a.employee_id._get_tz(a.date)).items():
            tz = ZoneInfo(tz_name)
            dates = tz_attendances.mapped('date')
            expected_by_employee = tz_attendances.employee_id._get_expected_attendances_batch(
                datetime.combine(min(dates), time.min, tz),
                datetime.combine(max(dates) + timedelta(days=1), time.min, tz),
            )
            for employee_id, shifts in expected_by_employee.items():
                for start, stop, _attendance in shifts:
                    # in UTC, so that a change of offset does not change the duration
                    duration = stop.astimezone(UTC) - start.astimezone(UTC)
                    hours_by_day[employee_id, start.astimezone(tz).date()] += duration.total_seconds() / 3600
        expected_by_attendance = {}
        for (employee, day), day_attendances in attendances_by_day.items():
            refused, day_attendances = day_attendances.partitioned(lambda a: a.state == 'refused')
            for attendance in refused:
                expected_by_attendance[attendance] = 0.0
            if not day_attendances:
                continue
            remaining = hours_by_day[employee.id, day]
            *previous, last = day_attendances.sorted(lambda a: a.check_in)
            for attendance in previous:
                expected = min(attendance.worked_hours, remaining)
                expected_by_attendance[attendance] = expected
                remaining -= expected
            expected_by_attendance[last] = remaining
        for attendance in attendances:
            attendance.expected_hours = expected_by_attendance[attendance]

    @api.depends('worked_hours', 'expected_hours', 'state', 'check_out')
    def _compute_overtime_hours(self):
        """Compute ``overtime_hours``: the worked minus the expected hours, nothing within the
        company's tolerance (``attendance_validation_tolerance``, in minutes). A refused attendance
        makes no overtime, an open one none yet."""
        for attendance in self:
            overtime = attendance.worked_hours - attendance.expected_hours
            tolerance = attendance.employee_id.company_id.attendance_validation_tolerance / 60
            if attendance.state == 'refused' or not attendance.check_out or abs(overtime) <= tolerance:
                overtime = 0.0
            attendance.overtime_hours = overtime

    def _recompute_expected_hours(self):
        """Mark the expected hours and the overtime of these attendances to recompute. A recomputed
        field does not mark the fields depending on it, so the overtime is marked as well, and
        ``has_issue`` (not stored) is reset."""
        for fname in ('expected_hours', 'overtime_hours'):
            self.env.add_to_compute(self._fields[fname], self)
        self.invalidate_recordset(['has_issue'])

    @api.depends('employee_id', 'check_in')
    def _compute_employee_tz(self):
        """Timezone of the employee on the check in day, for the form to warn when it differs from the browser's."""
        for attendance in self:
            if attendance.employee_id and attendance.check_in:
                # sudo() is needed because attendance officers may not have access to employee versions.
                attendance.employee_tz = attendance.employee_id.sudo()._get_version(attendance.check_in.date()).tz
            else:
                attendance.employee_tz = False

    @api.depends('employee_id', 'check_in', 'check_out', 'break_duration', 'in_mode', 'out_mode')
    def _compute_attendance_issues(self):
        """Flag the late check-ins and the early check-outs, see :meth:`_get_issues`."""
        # In a form, the attendances are new records, which _get_issues cannot find in the database. Their _origin is
        # the saved attendance.
        issues = self._origin._get_issues()
        for attendance in self:
            attendance.update({
                field_name: attendance._origin in flagged_attendances
                for field_name, flagged_attendances in issues.items()
            })

    @api.model
    def _get_worked_time_domain(self):
        """Return the domain of the attendances that count as worked time when looking for issues. The refused and
        technical attendances do not count.
        """
        return Domain("state", "!=", "refused") & Domain("in_mode", "!=", "technical")

    def _search_same_day_attendances(self, domain=Domain.TRUE):
        """Return the attendances of the same employees spanning the local days these span, ``self`` included: from
        the start of the local day of the check in to the end of the local day of the check out. So an attendance over
        midnight is found from both of its days.

        :param domain: extra domain on the returned attendances
        :rtype: hr.attendance
        """
        if not self:
            return self
        dummy = self.env['resource.calendar']
        windows_by_employee = defaultdict(list)
        for attendance in self:
            employee = attendance.employee_id
            tz = ZoneInfo(employee._get_tz(attendance.date))
            check_out_day = (attendance.check_out or attendance.check_in).replace(tzinfo=UTC).astimezone(tz).date()
            windows_by_employee[employee].append((
                datetime.combine(attendance.date, time.min, tz).astimezone(UTC),
                datetime.combine(check_out_day + timedelta(days=1), time.min, tz).astimezone(UTC),
                dummy,
            ))
        return self.sudo().search(domain & Domain.OR(
            Domain('employee_id', '=', employee._origin.id) & Domain.OR(
                Domain('check_in', '<', stop.replace(tzinfo=None)) & (
                    Domain('check_out', '>', start.replace(tzinfo=None))
                    | (Domain('check_out', '=', False) & Domain('check_in', '>=', start.replace(tzinfo=None))))
                for start, stop, _dummy in Intervals(windows)
            )
            for employee, windows in windows_by_employee.items()
        ))

    def _get_issues(self):
        """Find the late check-ins and the early check-outs on the days of the attendances in self. The overtimes and
        the undertimes are the ``overtime_hours`` of the attendances.

        Each day of an employee is compared with the shifts of their schedule on that day, give or take the company's
        tolerance (``attendance_validation_tolerance``, in minutes). A schedule may only give hours per day, without
        times (``duration_based``): such a day has no late check-in nor early check-out.

        - The first attendance of the day is a late check-in if it starts after the first shift.
        - The last attendance of the day is an early check-out if it ends before the end of the last shift.

        The early check-out is not flagged while the employee is still at work. It is not flagged either when the
        automatic check-out closed the day, because the employee did not leave at that time. They forgot to check out,
        and the attendance goes to review for that reason, see :meth:`_get_auto_review_domain`.

        Employees with a flexible schedule have no issue.

        :return: the flagged attendances of each issue field: ``is_late_check_in`` and ``is_early_check_out``
        :rtype: dict[str, hr.attendance]
        """
        issues = dict.fromkeys(("is_late_check_in", "is_early_check_out"), self.env["hr.attendance"])
        worked_attendances = self._search_same_day_attendances(self._get_worked_time_domain())
        for employee, employee_attendances in worked_attendances.grouped("employee_id").items():
            tolerance = timedelta(minutes=employee.company_id.attendance_validation_tolerance)
            attendances_by_day = employee_attendances.grouped("date")
            shifts_by_day = employee._get_expected_attendances_by_day(attendances_by_day)
            for day, shifts in shifts_by_day.items():
                day_attendances = attendances_by_day[day]
                # A schedule of hours per day has no times. Its shifts get made-up times around noon, which nobody is
                # expected to follow.
                has_times = shifts and not any(
                    calendar_attendances.filtered('duration_based') for *_, calendar_attendances in shifts
                )
                # the shifts are (start, stop, calendar attendances), sorted by start
                day_start, day_end = (shifts[0][0], shifts[-1][1]) if shifts else (None, None)
                first_attendance = min(day_attendances, key=lambda a: a.check_in)
                if has_times and first_attendance.check_in.replace(tzinfo=UTC) > day_start + tolerance:
                    issues["is_late_check_in"] |= first_attendance

                if not all(day_attendances.mapped("check_out")):
                    continue
                last_attendance = max(day_attendances, key=lambda a: a.check_out)
                if last_attendance.out_mode == "auto_check_out":
                    continue
                if has_times and last_attendance.check_out.replace(tzinfo=UTC) < day_end - tolerance:
                    issues["is_early_check_out"] |= last_attendance
        return issues

    def _recompute_same_day_issues(self):
        """Recompute the issues of all the attendances on the same days as the attendances in self.

        The issues of an attendance depend on the other attendances of its day. For example, a new attendance in the
        evening makes it the last attendance of the day, and the afternoon one is no longer an early check-out.
        ``@api.depends`` cannot express that, so :meth:`create`, :meth:`write` and :meth:`unlink` call this method.

        It returns the attendances that had an issue before, so that the callers can review the ones that have none
        left. The others stay as they are: an attendance a manager put back to To Review by hand is not reviewed again.

        :return: the attendances of the days that had an issue before the recompute
        :rtype: hr.attendance
        """
        same_day_attendances = self._search_same_day_attendances()
        had_issue = same_day_attendances.filtered("has_issue")
        for fname in ("is_late_check_in", "is_early_check_out"):
            self.env.add_to_compute(self._fields[fname], same_day_attendances)
        # has_issue is not stored, so add_to_compute does not reset it
        same_day_attendances.invalidate_recordset(["has_issue"])
        return had_issue

    @api.depends('is_late_check_in', 'is_early_check_out', 'overtime_hours')
    def _compute_has_issue(self):
        for attendance in self:
            attendance.has_issue = (
                attendance.is_late_check_in
                or attendance.is_early_check_out
                or attendance.overtime_hours != 0
            )

    @api.constrains('break_duration', 'check_in', 'check_out')
    def _check_break_duration(self):
        """Check that ``break_duration`` is positive, only set on closed attendances and not
        longer than the attendance.

        :raise ValidationError: if one of these conditions is not met
        """
        for attendance in self:
            if float_compare(attendance.break_duration, 0.0, precision_digits=4) < 0:
                raise ValidationError(self.env._("Break duration cannot be negative."))
            if not attendance.check_out and not float_is_zero(attendance.break_duration, precision_digits=4):
                raise ValidationError(self.env._(
                    "You can only set a break duration once the employee has checked out."
                ))
            if attendance.check_in and attendance.check_out and attendance.break_duration:
                total_hours = time_to_float(attendance.check_out - attendance.check_in)
                if float_compare(attendance.break_duration, total_hours, precision_digits=4) > 0:
                    raise ValidationError(self.env._("Breaks cannot be longer than the attendance time"))

    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """Check that ``check_out`` is not earlier than ``check_in``.

        :raise ValidationError: if it is
        """
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                if attendance.check_out < attendance.check_in:
                    raise exceptions.ValidationError(_('"Check Out" time cannot be earlier than "Check In" time.'))

    @api.constrains('check_in', 'check_out', 'employee_id', 'state')
    def _check_validity(self):
        """Check the attendance against the other attendances of the employee.

        An employee has at most one open attendance (without ``check_out``) and no overlapping
        attendances. A refused attendance did not happen: it is neither checked nor conflicts with
        the others, until its refusal is taken back. Skipped when the context has
        ``skip_time_rules``, i.e. for the automatic check-out.

        The attendances that can conflict with the batch are read in one search, restricted to
        the periods of the batch (its attendances less than a day apart) and to the open
        attendances. Each attendance is then compared to its neighbours: the previous attendance
        of the employee must be over when it starts and no other may start before it ends,
        e.g. 08:00-12:00 conflicts with 11:00-13:00 but not with 12:00-13:00.

        :raise ValidationError: if the attendance overlaps another one or if another attendance
            of the employee is still open
        """
        if self.env.context.get('skip_time_rules'):
            return
        to_check = self.filtered(lambda attendance: attendance.state != 'refused')
        # one period per group of attendances less than a day apart, so that attendances far
        # apart in time (e.g. 2024 and 2026) don't read all the attendances in between
        periods = []
        for start, stop in sorted((attendance.check_in, attendance.check_out or attendance.check_in) for attendance in to_check):
            if periods and start <= periods[-1][1] + timedelta(days=1):
                periods[-1][1] = max(periods[-1][1], stop)
            else:
                periods.append([start, stop])
        candidates = self.env['hr.attendance'].search_fetch(
            Domain('employee_id', 'in', to_check.employee_id.ids) & Domain('state', '!=', 'refused') & (
                Domain.OR(Domain('check_in', '<=', stop) & Domain('check_out', '>=', start) for start, stop in periods)
                | Domain('check_out', '=', False)
            ),
            ['employee_id', 'check_in', 'check_out'],
            order='check_in, id',
        )
        candidates_by_employee = candidates.grouped('employee_id')
        for employee, attendances in to_check.grouped('employee_id').items():
            # empty when the only attendance of the employee is the one being made invalid
            employee_candidates = list(candidates_by_employee.get(employee, []))
            check_ins = [candidate.check_in for candidate in employee_candidates]
            open_candidates = [candidate for candidate in employee_candidates if not candidate.check_out]
            for attendance in attendances:
                index = bisect_right(check_ins, attendance.check_in)
                # the attendance itself is among the candidates starting before it: skip it
                previous_candidates = [candidate for candidate in employee_candidates[max(index - 2, 0):index] if candidate != attendance]
                previous = previous_candidates[-1] if previous_candidates else None
                if previous and previous.check_out and previous.check_out > attendance.check_in:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s",
                                                       empl_name=employee.name,
                                                       datetime=format_datetime(self.env, previous.check_in, dt_format=False)))
                if not attendance.check_out:
                    if other_open := [candidate for candidate in open_candidates if candidate != attendance]:
                        raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee hasn't checked out since %(datetime)s",
                                                           empl_name=employee.name,
                                                           datetime=format_datetime(self.env, other_open[-1].check_in, dt_format=False)))
                elif starting_during := employee_candidates[index:bisect_left(check_ins, attendance.check_out)]:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s",
                                                       empl_name=employee.name,
                                                       datetime=format_datetime(self.env, starting_during[-1].check_in, dt_format=False)))

    def _get_break_rule_lines(self):
        """Return the break rule line of each closed attendance: the line of the employee's break rule with the highest
        hours that the attendance (``check_out - check_in``) exceeds.

        :return: ``{attendance: hr.attendance.break.rule.line}``, only the attendances with a line
        :rtype: dict
        """
        attendances = self.filtered('check_out')
        rule_by_employee = self.env['hr.attendance.break.rule']._get_rule_by_employee(attendances.employee_id)
        result = {}
        for attendance in attendances:
            if not (rule := rule_by_employee.get(attendance.employee_id)):
                continue
            if line := rule._get_line(time_to_float(attendance.check_out - attendance.check_in)):
                result[attendance] = line
        return result

    def _get_break_rule_raises(self):
        """Return the attendances whose break is below the minimum break of their break rule line.

        :return: ``{minimum break: attendances}``
        :rtype: dict
        """
        to_raise = defaultdict(self.browse)
        for attendance, line in self._get_break_rule_lines().items():
            if float_compare(attendance.break_duration, line.break_hours, precision_digits=4) < 0:
                to_raise[line.break_hours] |= attendance
        return to_raise

    # The fields that a manager approves when reviewing an attendance. When one of them changes, the issues of its day
    # may change. When the employee changes one of them, the attendance needs a new review.
    _REVIEWED_FIELDS = frozenset({'check_in', 'check_out', 'break_duration', 'employee_id'})

    def write(self, vals):
        """Write the values on the attendances, and follow up on the changes of the reviewed fields
        (``_REVIEWED_FIELDS``).

        - A check-in or check-out time changed by a user becomes encoded by hand (``manual`` mode), unless the values
          give the mode. The kiosk, the systray and the automatic check-out write as superuser and keep their mode.
        - An attendance changed by its employee goes back to To Review until a manager reviews it again. So does an
          attendance that a manager gives to an employee they do not manage (their own), and its times become encoded
          by hand. An attendance changed by a manager keeps its state, and :meth:`_auto_review` may review it.
        - The issues of the days of the attendance are recomputed, and :meth:`_auto_review` may review the other
          attendances of those days that no longer have an issue.
        - The attendances of the days the written ones left or joined share their expected hours again.

        Refusing an attendance, or taking back its refusal, also recomputes the issues and the expected hours of its
        days, because it stops or starts counting as worked time.

        :param dict vals: the values to write
        :raise AccessError: see :meth:`_check_write_access`
        """
        self._check_write_access(vals)
        changes_reviewed_fields = bool(self._REVIEWED_FIELDS & vals.keys())
        changes_refusal = "state" in vals and any((a.state == "refused") != (vals["state"] == "refused") for a in self)
        if not changes_reviewed_fields and not changes_refusal:
            return super().write(vals)

        # Giving an attendance to an employee the user does not manage (their own) is not a manager's edit: it must not
        # keep a review state that the user may not give.
        gives_to_unmanaged = not self._is_manager_of_new_employee(vals)
        edited_by_manager, edited_by_employee = self.partitioned(
            lambda a: self.env.su or (a.is_manager and not gives_to_unmanaged),
        )
        # A time changed by a user is encoded by hand. The kiosk, the systray and the automatic check-out write as
        # superuser and keep their mode.
        manual_modes = {}
        if not self.env.su:
            if "check_in" in vals:
                manual_modes["in_mode"] = "manual"
            if "check_out" in vals:
                manual_modes["out_mode"] = "manual"
        # a manager may give another mode, an employee may not
        manager_vals = {**manual_modes, **vals}
        employee_vals = {**vals, **manual_modes, "state": "draft"}

        # The write can move the attendances to other days, so the attendances of their current days are searched now.
        same_day_attendances_before = self._search_same_day_attendances() - self

        # A device recorded the times of another employee: they are encoded by hand for the new one, so that the
        # review by exception does not review them without a manager.
        moved_to_unmanaged = edited_by_employee.filtered(
            lambda a: gives_to_unmanaged and a.employee_id.id != vals["employee_id"],
        )

        super(HrAttendance, edited_by_manager).write(manager_vals)
        super(HrAttendance, edited_by_employee - moved_to_unmanaged).write(employee_vals)
        super(HrAttendance, moved_to_unmanaged).write({**employee_vals, "in_mode": "manual", "out_mode": "manual"})
        if changes_reviewed_fields:
            for break_hours, attendances in self._get_break_rule_raises().items():
                # sudo: the rule applies whoever writes the attendance
                super(HrAttendance, attendances.sudo()).write({'break_duration': break_hours})

        # the issues first: they read has_issue before the overtime changes
        had_issue = (same_day_attendances_before | self)._recompute_same_day_issues()
        if changes_reviewed_fields or changes_refusal:
            (same_day_attendances_before | self._search_same_day_attendances())._recompute_expected_hours()

        if not self.env.context.get("skip_time_rules"):
            if "state" not in vals:
                edited_by_manager._auto_review()
            (had_issue - self)._auto_review()

        return True

    def _check_write_access(self, vals):
        """Check that the user may write the values on the attendances.

        - Only an attendance manager can give an attendance to another employee than the user, and only a user who may
          edit their own attendances (``group_hr_attendance_own``) can give one to themselves.
        - Only an attendance manager can review an attendance or set its mode to a device mode, see
          :meth:`_requires_attendance_manager`, and only for an employee they manage.

        :raise AccessError: if the user may not write the values
        """
        if self.env.su:
            return
        if (
            vals.get("employee_id")
            and not (
                vals["employee_id"] in self.env.user.employee_ids.ids
                and self.env.user.has_group("hr_attendance.group_hr_attendance_own")
            )
            and not self.env["hr.employee"].browse(vals["employee_id"])._filter_attendance_managed_by_current_user()
        ):
            raise AccessError(
                self.env._("You can only assign attendances to yourself or to the employees whose attendances you manage.")
            )
        if self._requires_attendance_manager(vals) and (
            not all(self.mapped("is_manager")) or not self._is_manager_of_new_employee(vals)
        ):
            raise AccessError(self.env._("Only the attendance managers of the employees can review their attendances."))

    def _is_manager_of_new_employee(self, vals):
        """Return whether the user manages the employee that the values give the attendances to, if they give one.

        :param dict vals: the values to write
        :rtype: bool
        """
        return (
            self.env.su
            or not vals.get("employee_id")
            or bool(self.env["hr.employee"].browse(vals["employee_id"])._filter_attendance_managed_by_current_user())
        )

    @api.model
    def _requires_attendance_manager(self, vals):
        """Return whether only an attendance manager may write these values on an attendance.

        That is the case when the values review or refuse the attendance, or give its check-in or check-out a device
        mode (kiosk, systray, ...). The kiosk and the systray write these values as superuser.

        :param dict vals: the values to write
        :rtype: bool
        """
        return (
            vals.get("state", "draft") != "draft"
            or any(vals.get(mode, "manual") != "manual" for mode in ("in_mode", "out_mode"))
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_recompute_same_day_issues(self):
        """Recompute the issues and the expected hours of the other attendances on the days of the deleted
        attendances. The ones that no longer have an issue may be reviewed by :meth:`_auto_review`."""
        same_day_attendances = self._search_same_day_attendances() - self

        def recompute():
            had_issue = same_day_attendances._recompute_same_day_issues()
            same_day_attendances._recompute_expected_hours()
            had_issue._auto_review()
        return recompute

    def copy(self, default=None):
        raise exceptions.UserError(_('You cannot duplicate an attendance.'))

    def _creation_message(self):
        return self._get_check_in_out_log('in')

    def _get_check_in_out_log(self, direction):
        """Return the chatter message logged when the employee checks in or out.

        The message gives the mode (kiosk, systray, ...) and the location. When the GPS position is known, the
        location links to Google Maps. The browser and the IP address, when known, follow on a second, muted line.

        :param str direction: ``'in'`` or ``'out'``
        :return: the body of the message
        :rtype: str | Markup
        """
        self.ensure_one()
        mode = dict(self._fields[f'{direction}_mode']._description_selection(self.env)).get(self[f'{direction}_mode'])
        latitude, longitude = self[f'{direction}_latitude'], self[f'{direction}_longitude']
        location = self[f'{direction}_location']
        if latitude or longitude:
            location = Markup('<a href="%s" target="_blank">%s</a>') % (
                get_google_maps_url(latitude, longitude), location or f"{latitude}, {longitude}")
        if direction == 'in':
            if location:
                message = self.env._("Check in from %(location)s (%(mode)s)", location=location, mode=mode)
            else:
                message = self.env._("Check in (%(mode)s)", mode=mode)
        elif location:
            message = self.env._("Check out from %(location)s (%(mode)s)", location=location, mode=mode)
        else:
            message = self.env._("Check out (%(mode)s)", mode=mode)

        details = []
        if browser := self[f'{direction}_browser']:
            details.append(self.env._("Browser: %(browser)s", browser=browser))
        if ip_address := self[f'{direction}_ip_address']:
            details.append(self.env._("IP address: %(ip_address)s", ip_address=ip_address))
        if not details:
            return message
        return Markup('%s<br/><span class="text-muted">%s</span>') % (message, " · ".join(details))

    def action_in_attendance_maps(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': get_google_maps_url(self.in_latitude, self.in_longitude),
            'target': 'new'
        }

    def action_out_attendance_maps(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': get_google_maps_url(self.out_latitude, self.out_longitude),
            'target': 'new'
        }

    def get_kiosk_url(self):
        """Return the public kiosk URL of the current company (base URL + kiosk key).

        :rtype: str
        """
        return self.get_base_url() + "/hr_attendance/" + self.env.company.attendance_kiosk_key

    @api.model
    def has_demo_data(self):
        if not self.env.user.has_group("hr_attendance.group_hr_attendance_user"):
            return True
        # This record only exists if the scenario has been already launched
        demo_tag = self.env.ref('hr_attendance.resource_calendar_std_38h', raise_if_not_found=False)
        return bool(demo_tag) or bool(self.env['ir.module.module'].search_count([('demo', '=', True)]))

    @api.model
    def get_help_data(self, domain):
        """Return the data of the help view (see `hr_attendance_view_help`). On My Attendances, the help welcomes the
        employee by their name, which depends on the company."""
        data = {'can_load_demo': not self.has_demo_data()}
        if self.env.context.get('my_attendances'):
            data['welcome'] = self.env._(
                "Welcome %(employee_name)s! Log your attendances here.",
                employee_name=self.env.user.employee_id.name or self.env.user.name,
            )
        return data

    def _load_demo_data(self):
        if self.has_demo_data():
            return
        env_sudo = self.sudo().with_context({}).env
        env_sudo['hr.employee']._load_scenario()
        # Load employees, schedules, departments and partners
        convert.convert_file(env_sudo, 'hr_attendance', 'data/scenarios/hr_attendance_scenario.xml', None, mode='init')

        employee_sj = self.env.ref('hr.employee_sj')
        employee_mw = self.env.ref('hr.employee_mw')
        employee_eg = self.env.ref('hr.employee_eg')

        # Retrieve employee from xml file
        # Calculate attendances records for the previous month and the current until today
        now = datetime.now()
        previous_month_datetime = (now - relativedelta(months=1))
        # Ensure employees have a valid contract start date (so attendances render in the Gantt view)
        employees = employee_sj | employee_mw | employee_eg
        employees.write({
            'contract_date_start': (now - relativedelta(months=2)).date(),
        })
        date_range = now.day + monthrange(previous_month_datetime.year, previous_month_datetime.month)[1]
        # precise GPS positions, as sent by a browser allowed to share its location
        city_dict = {
            'latitude': 50.6326412,
            'longitude': 4.8670315,
            'city': 'Ramillies',
        }
        city_exception_dict = {
            'latitude': 50.8465573,
            'longitude': 4.3517210,
            'city': 'Brussels',
        }
        attendance_values = []
        for i in range(1, date_range):
            check_in_date = now.replace(hour=6, minute=0, second=randint(0, 59)) + timedelta(days=-i, minutes=randint(-2, 3))
            if check_in_date.weekday() not in range(0, 5):
                continue
            check_out_date = now.replace(hour=10, minute=0, second=randint(0, 59)) + timedelta(days=-i, minutes=randint(-2, -1))
            check_in_date_after_lunch = now.replace(hour=11, minute=0, second=randint(0, 59)) + timedelta(days=-i, minutes=randint(-2, -1))
            check_out_date_after_lunch = now.replace(hour=15, minute=0, second=randint(0, 59)) + timedelta(days=-i, minutes=randint(1, 3))

            # employee_eg doesn't work on friday
            eg_data = []
            if check_in_date.weekday() != 4:
                # employee_eg will compensate her work's hours between weeks.
                if check_in_date.isocalendar().week % 2:
                    employee_eg_hours = {
                        'check_in_date': check_in_date + timedelta(hours=1),
                        'check_out_date': check_out_date,
                        'check_in_date_after_lunch': check_in_date_after_lunch,
                        'check_out_date_after_lunch': check_out_date_after_lunch + timedelta(hours=-1),
                    }
                else:
                    employee_eg_hours = {
                        'check_in_date': check_in_date,
                        'check_out_date': check_out_date,
                        'check_in_date_after_lunch': check_in_date_after_lunch,
                        'check_out_date_after_lunch': check_out_date_after_lunch + timedelta(hours=1, minutes=30),
                    }
                eg_data = [{
                    'employee_id': employee_eg.id,
                    'check_in': employee_eg_hours['check_in_date'],
                    'check_out': employee_eg_hours['check_out_date'],
                    'in_mode': "kiosk",
                    'out_mode': "kiosk"
                }, {
                    'employee_id': employee_eg.id,
                    'check_in': employee_eg_hours['check_in_date_after_lunch'],
                    'check_out': employee_eg_hours['check_out_date_after_lunch'],
                    'in_mode': "kiosk",
                    'out_mode': "kiosk",
                }]

            # calculate GPS coordination for employee_mw (systray attendance)
            if randint(1, 10) == 1:
                city_data = city_exception_dict
            else:
                city_data = city_dict
            mw_data = [{
                'employee_id': employee_mw.id,
                'check_in': check_in_date,
                'check_out': check_out_date,
                'in_mode': "systray",
                'out_mode': "systray",
                'in_longitude': city_data['longitude'],
                'out_longitude': city_data['longitude'],
                'in_latitude': city_data['latitude'],
                'out_latitude': city_data['latitude'],
                'in_location': city_data['city'],
                'out_location': city_data['city'],
                'in_ip_address': "127.0.0.1",
                'out_ip_address': "127.0.0.1",
                'in_browser': 'chrome',
                'out_browser': 'chrome'
            }, {
                'employee_id': employee_mw.id,
                'check_in': check_in_date_after_lunch,
                'check_out': check_out_date_after_lunch,
                'in_mode': "systray",
                'out_mode': "systray",
                'in_longitude': city_data['longitude'],
                'out_longitude': city_data['longitude'],
                'in_latitude': city_data['latitude'],
                'out_latitude': city_data['latitude'],
                'in_location': city_data['city'],
                'out_location': city_data['city'],
                'in_ip_address': "127.0.0.1",
                'out_ip_address': "127.0.0.1",
                'in_browser': 'chrome',
                'out_browser': 'chrome'
            }]
            sj_data = [{
                'employee_id': employee_sj.id,
                'check_in': check_in_date + timedelta(minutes=randint(-10, -5)),
                'check_out': check_out_date,
                'in_mode': "manual",
                'out_mode': "manual"
            }, {
                'employee_id': employee_sj.id,
                'check_in': check_in_date_after_lunch,
                'check_out': check_out_date_after_lunch + timedelta(hours=1, minutes=randint(-20, 10)),
                'in_mode': "manual",
                'out_mode': "manual"
            }]
            attendance_values.extend(eg_data + mw_data + sj_data)
        # forgotten check-out yesterday evening, and at work today
        yesterday_check_in = now.replace(hour=17, minute=randint(30, 59)) - timedelta(days=1)
        attendance_values.extend([{
            'employee_id': employee_sj.id,
            'check_in': yesterday_check_in,
            'in_mode': "kiosk",
        }, {
            'employee_id': employee_mw.id,
            'check_in': now - timedelta(hours=1, minutes=randint(0, 30)),
            'in_mode': "systray",
            'in_latitude': city_dict['latitude'],
            'in_longitude': city_dict['longitude'],
            'in_location': city_dict['city'],
            'in_ip_address': "127.0.0.1",
            'in_browser': 'chrome',
        }])
        attendances = self.env['hr.attendance'].create(attendance_values)
        # one refused attendance among the manual ones
        attendances.filtered(lambda a: a.employee_id == employee_sj and a.check_out)[:1].action_refuse()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_try_kiosk(self):
        if not self.env.user.has_group("hr_attendance.group_hr_attendance_user"):
            return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("You don't have the rights to execute that action."),
                        'type': 'info',
                    }
            }
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.env.company.attendance_kiosk_url + '?from_trial_mode=True'
        }

    def _cron_auto_check_out(self):
        """Cron: check out the forgotten open attendances, for the companies with
        ``auto_check_out``, in ``tolerance`` and in ``specific_time`` mode."""
        self._cron_auto_check_out_tolerance()
        self._cron_auto_check_out_specific_time()

    def _cron_auto_check_out_tolerance(self):
        """Check out the employees who forgot to, once they have worked the hours of their schedule for the day and
        the company's tolerance (``auto_check_out_tolerance``) has passed.

        This is for the companies that check out automatically after a tolerance (``auto_check_out_mode``), and for
        the employees whose schedule is not flexible. The attendance is closed once it has worked its expected hours
        (``expected_hours``: what the other attendances of the day leave of the day's schedule). The tolerance only
        delays the check-out, it adds no worked time. The check-out mode is ``auto_check_out``, and a message is
        posted on the attendance.
        """
        to_verify = self.search([
            ("check_out", "=", False),
            ("employee_id.company_id.auto_check_out", "=", True),
            ("employee_id.company_id.auto_check_out_mode", "=", "tolerance"),
            ("employee_id.resource_calendar_id.calendar_type", "!=", "undefined"),
        ])
        now = fields.Datetime.now()
        for employee, attendances in to_verify.grouped("employee_id").items():
            tolerance = timedelta(hours=employee.company_id.auto_check_out_tolerance)
            for attendance in attendances:
                # a flexible schedule expects no hours
                if employee._get_version(attendance.date)._is_flexible():
                    continue
                expected_check_out = attendance.check_in + timedelta(hours=attendance.expected_hours)
                if now <= expected_check_out + tolerance:
                    continue
                attendance.write({
                    "check_out": max(expected_check_out, attendance.check_in + timedelta(seconds=1)),
                    "out_mode": "auto_check_out",
                })
                attendance.message_post(
                    body=self.env._(
                        "This attendance was automatically checked out because the employee exceeded the allowed time for their scheduled work hours.",
                    ),
                )

    def _cron_absence_detection(self):
        """Cron: create a validated technical attendance for each employee without attendance on a
        day since the last call of the cron, up to yesterday. A refused attendance did not happen:
        a day with only refused attendances is an absence.

        Only for the employees whose current version takes its work entries from the attendances
        and is in contract that day, and for the days expecting hours
        (``hr.employee._get_expected_attendances_batch``). The attendance starts and ends when the
        first expected shift of the day starts, so that it has no worked hours and its overtime is
        the opposite of the expected hours of the day.
        """
        yesterday = fields.Date.today() - timedelta(days=1)
        lastcall = self.env.context.get('lastcall')
        first_day = min(lastcall.date(), yesterday) if lastcall else yesterday

        employees = self.env['hr.employee'].search([
            ('current_version_id.work_entry_source', '=', 'attendance'),
            ('current_version_id.contract_date_start', '<=', yesterday),
            '|',
                ('current_version_id.contract_date_end', '=', False),
                ('current_version_id.contract_date_end', '>=', first_day),
        ])
        checked_in = {
            (employee.id, day)
            for employee, day in self.env['hr.attendance']._read_group(
                [
                    ('employee_id', 'in', employees.ids), ('date', '>=', first_day), ('date', '<=', yesterday),
                    ('state', '!=', 'refused'),
                ],
                ['employee_id', 'date:day'],
            )
        }
        # a day before and after, for the local days of all the timezones
        expected_by_employee = employees._get_expected_attendances_batch(
            datetime.combine(first_day - timedelta(days=1), time.min, UTC),
            datetime.combine(yesterday + timedelta(days=2), time.min, UTC),
        )

        dummy = self.env['resource.calendar.attendance']
        technical_attendances_vals = []
        for employee in employees:
            version = employee.current_version_id
            for day in rrule(DAILY, dtstart=first_day, until=yesterday):
                day = day.date()
                if (employee.id, day) in checked_in \
                        or day < version.contract_date_start \
                        or (version.contract_date_end and day > version.contract_date_end):
                    continue
                tz = ZoneInfo(employee._get_tz(day))
                shifts = expected_by_employee[employee.id] & Intervals([(
                    datetime.combine(day, time.min, tz), datetime.combine(day + timedelta(days=1), time.min, tz), dummy,
                )])
                if not shifts:
                    continue
                shift_start = next(iter(shifts))[0].astimezone(UTC).replace(tzinfo=None)
                technical_attendances_vals.append({
                    'check_in': shift_start,
                    'check_out': shift_start,
                    'in_mode': 'technical',
                    'out_mode': 'technical',
                    'employee_id': employee.id,
                    'state': 'validated',
                })

        technical_attendances = self.create(technical_attendances_vals)
        body = self.env._('This attendance was automatically created to cover an unjustified absence on that day.')
        for technical_attendance in technical_attendances:
            technical_attendance.message_post(body=body)

    def _cron_auto_check_out_specific_time(self):
        """Check out the open attendances once the company's ``auto_check_out_specific_time``
        is reached.

        Applies to the companies in ``specific_time`` mode. The check-out is the first
        occurrence of that hour (employee's timezone) after the check-in, as soon as it is past,
        with ``out_mode = 'auto_check_out'``; a message is posted.
        """
        current_utc_dt = fields.Datetime.now()
        utc_tz = ZoneInfo('UTC')
        all_open_attendances = self.search([
            ('check_out', '=', False),
            ('employee_id.company_id', 'any', [
                ('auto_check_out', '=', True),
                ('auto_check_out_mode', '=', 'specific_time'),
            ]),
        ])

        for company, company_attendances in all_open_attendances.grouped(lambda att: att.employee_id.company_id).items():
            cutoff_time = float_to_time(company.auto_check_out_specific_time)
            cutoff_hour, cutoff_minute = cutoff_time.hour, cutoff_time.minute
            for att in company_attendances:
                employee_tz = ZoneInfo(att.employee_id._get_tz())
                current_employee_dt = current_utc_dt.astimezone(employee_tz)
                check_in_employee_dt = att.check_in.astimezone(employee_tz)
                same_day_cutoff_dt = check_in_employee_dt.replace(
                    hour=cutoff_hour, minute=cutoff_minute, second=0, microsecond=0,
                )

                if check_in_employee_dt.time() < same_day_cutoff_dt.time():
                    next_cutoff = same_day_cutoff_dt
                else:
                    next_cutoff = same_day_cutoff_dt + relativedelta(days=1)

                if current_employee_dt < next_cutoff:
                    continue

                employee_checkout = next_cutoff.astimezone(utc_tz).replace(tzinfo=None)
                employee_checkout = max(employee_checkout, att.check_in + relativedelta(seconds=1))

                att.write({
                    'check_out': employee_checkout,
                    'out_mode': 'auto_check_out',
                })

                att.message_post(body=self.env._(
                    'This attendance was automatically checked out based on company specific time configuration.',
                ))

    def _get_localized_times(self):
        """Return ``check_in`` and ``check_out`` in the timezone of the employee's version.

        The attendance must be closed.

        :return: ``(check_in, check_out)``, naive local datetimes
        :rtype: tuple
        """
        self.ensure_one()
        tz = ZoneInfo(self.employee_id.sudo()._get_version(self.check_in.date()).tz)
        localized_start = self.check_in.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        localized_end = self.check_out.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        return localized_start, localized_end

    def _get_break_duration_within_period(self, start, stop):
        """Return the part of the break durations of ``self`` falling within a period.

        The break of each closed attendance is prorated to the share of the attendance that lies
        within ``[start, stop]``.

        :param datetime start: naive local datetime (employee's timezone)
        :param datetime stop: naive local datetime
        :return: hours
        :rtype: float
        """
        attendances = self.filtered(lambda attendance: attendance.check_out and attendance.break_duration)
        if not attendances:
            return 0.0

        attendance_intervals = Intervals([
            (*attendance._get_localized_times(), attendance)
            for attendance in attendances
        ], keep_distinct=True)
        period_interval = Intervals([(start, stop, self.env['resource.calendar'])])
        break_duration = 0.0
        for start, stop, attendance in attendance_intervals & period_interval:
            attendance_duration = time_to_float(attendance.check_out - attendance.check_in)
            break_duration += (
                time_to_float(stop - start) / attendance_duration
            ) * attendance.break_duration
        return break_duration

    def init(self):
        super().init()
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS hr_attendance_check_in_check_out_employee_id
            ON hr_attendance (check_in, check_out, employee_id);
        """)

    def _auto_review(self):
        """Mark as Reviewed the attendances that a manager does not need to look at.

        That is only for the companies that review the exceptions only (``attendance_validation``). There, an
        attendance is reviewed at check-out, unless it has an issue, one of its times was encoded by hand, or the
        employee forgot to check out (automatic check-out).
        """
        if to_review := self._filter_auto_reviewable():
            # The company's setting reviews them, not the user who checked out, so this runs as superuser.
            to_review.sudo().with_context(tracking_disable=True).write({"state": "validated"})

    def _filter_auto_reviewable(self):
        """Return the attendances that are reviewed at check-out, without a manager."""
        return self.filtered_domain([
            ("state", "=", "draft"),
            ("check_out", "!=", False),
            ("employee_id.company_id.attendance_validation", "=", "exception_validation"),
            # an unknown mode is not a device, so only a manager reviews it
            ("in_mode", "not in", (False, "manual")),
            ("out_mode", "not in", (False, "manual", "auto_check_out")),
            ("has_issue", "=", False),
        ])

    @api.model_create_multi
    def create(self, vals_list):
        """Create the attendances.

        A closed attendance that an attendance manager encodes by hand is Reviewed at once. An open one is reviewed
        at check-out, so the manager sees the day once it is over. The other attendances are To
        Review, and :meth:`_auto_review` may review them. The new attendances can remove the issues of the other
        attendances of their days, so those may be reviewed too. The other attendances of their days share their
        expected hours with them.

        :param list[dict] vals_list: the values of the attendances
        :raise AccessError: if a user who is not an attendance manager of the employee creates a reviewed attendance,
            or one with a device mode, see :meth:`_requires_attendance_manager`
        """
        # an attendance without employee gets the user's employee
        employee_ids = [vals.get("employee_id") or self._default_employee().id for vals in vals_list]
        employees = (
            self.env["hr.employee"].browse(vals["employee_id"] for vals in vals_list if vals.get("employee_id"))
            | self._default_employee()
        )
        managed_employee_ids = employees._filter_attendance_managed_by_current_user().ids
        for vals, employee_id in zip(vals_list, employee_ids):
            if vals.get("check_out"):
                vals.setdefault("out_mode", "manual")
            if self.env.su or employee_id in managed_employee_ids:
                if vals.get("in_mode", "manual") == "manual" and vals.get("check_out"):
                    vals.setdefault("state", "validated")
            elif self._requires_attendance_manager(vals):
                raise AccessError(
                    self.env._("Only the attendance managers of the employees can review their attendances."),
                )
        attendances = super().create(vals_list)
        for break_hours, to_raise in attendances._get_break_rule_raises().items():
            # sudo: the rule applies whoever creates the attendance
            super(HrAttendance, to_raise.sudo()).write({'break_duration': break_hours})
        # the new attendances change the issues of the other attendances of their days
        had_issue = attendances.filtered_domain(self._get_worked_time_domain())._recompute_same_day_issues()
        (attendances._search_same_day_attendances() - attendances)._recompute_expected_hours()
        (attendances | had_issue)._auto_review()
        return attendances

    def action_validate(self):
        """Validate the attendances. The attendances the user may not review, and the open ones, are skipped: a
        selection in the list can hold the user's own attendances, and an open attendance is reviewed once checked
        out."""
        self._filter_reviewable().filtered("check_out").write({'state': 'validated'})

    def action_refuse(self):
        """Refuse the attendances. The attendances the user may not review are skipped."""
        self._filter_reviewable().write({'state': 'refused'})

    def _filter_reviewable(self):
        """Return the attendances the user may review (approve or refuse)."""
        return self if self.env.su else self.filtered("is_manager")

    def action_reset_to_draft(self):
        """Set the attendances back to draft."""
        self.write({'state': 'draft'})

    @api.model
    def get_attendance_dashboard_data(self, domain=None):
        """Return the counters shown above the attendance lists, among the attendances the user
        can read. The domains match the filters of the search views.

        :param list domain: the domain of the action showing the counters
        :return: ``{counter: number of attendances}``
        :rtype: dict
        """
        domains = {
            'to_review': [('state', '=', 'draft'), ('check_out', '!=', False)],
            'late_check_in': [('is_late_check_in', '=', True)],
            'early_check_out': [('is_early_check_out', '=', True)],
            'no_check_out': [('out_mode', '=', 'auto_check_out')],
            'overtime': [('overtime_hours', '>', 0)],
            'undertime': [('overtime_hours', '<', 0)],
            'at_work': [('check_out', '=', False)],
        }
        # like the attendance list, the counters ignore the archived employees
        action_domain = Domain(domain or Domain.TRUE) & Domain('employee_id.active', '=', True)
        return {
            counter: self.search_count(action_domain & Domain(counter_domain))
            for counter, counter_domain in domains.items()
        }

    @api.model
    def _get_to_review_action(self):
        """Return the dashboard action showing the attendances to review (To Review menu).

        :rtype: dict
        """
        action = self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_attendance_action')
        # without its own path, the action keeps the one of the To Review menu in the URL
        del action['path']
        name = self.env._("To Review")
        action.update({
            'name': name,
            'display_name': name,
            'context': {'search_default_state_draft': 1},
            # the counters and the review buttons are on the list
            'views': sorted(action['views'], key=lambda view: view[1] != 'list'),
        })
        return action

    @api.model
    def _get_home_action(self):
        """Return the action of the Attendances app: the dashboard for the users who manage
        attendances; for the others, their attendances, or on small screens the check in/out
        panel of the systray when they may check in from Odoo.

        :rtype: dict
        """
        if self.env.user.has_group('hr_attendance.group_hr_attendance_officer'):
            return self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_attendance_action')
        employee = self.env.user.employee_id
        if employee and employee._has_attendance_check_in_ability():
            return self.env['ir.actions.actions']._for_xml_id('hr_attendance.hr_attendance_action_my_attendance')
        return self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_attendance_my_action')

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        """Return the unusual days of the employee of the context key ``employee_id``, or else
        of the current user's employee, see ``hr.employee._get_unusual_days``.

        :return: ``{'YYYY-MM-DD': bool}``
        :rtype: dict
        """
        employee_id = self.env.context.get('employee_id', False)
        employee = self.env['hr.employee'].browse(employee_id) if employee_id else self.env.user.employee_id
        return employee.sudo(False)._get_unusual_days(date_from, date_to)

    @api.model
    def get_working_hours_for_calendar(self, employee_id, date_from, date_to):
        """Return FullCalendar `businessHours` for the employee.

        :param employee_id: ID of the employee.
        :param date_from: Start date (YYYY-MM-DD).
        :param date_to: End date (YYYY-MM-DD).
        """
        employee = self.env["hr.employee"].browse(employee_id).exists()
        if not employee:
            return []

        tz = self.env.tz
        start_period = datetime.combine(fields.Date.to_date(date_from), time.min, tz)
        stop_period = datetime.combine(fields.Date.to_date(date_to) + timedelta(days=1), time.min, tz)
        # Include adjacent employee-local dates and generate complete duration-based days.
        query_start = start_period.astimezone(UTC) - timedelta(days=1)
        query_stop = stop_period.astimezone(UTC) + timedelta(days=1)
        calendar_periods = employee.sudo()._get_version_periods(
            query_start.date(), query_stop.date(), ['resource_calendar_id', 'tz'], check_contract=True,
        ).get(employee, [])
        calendar_periods = [
            (start, stop, (calendar, employee_tz))
            for start, stop, (calendar, employee_tz) in calendar_periods
            if datetime.combine(start, time.min, ZoneInfo(employee_tz)) < stop_period
            and datetime.combine(stop + timedelta(days=1), time.min, ZoneInfo(employee_tz)) > start_period
        ]
        if not calendar_periods:
            calendar_periods = [(
                query_start.date(), query_stop.date(),
                (employee.resource_calendar_id, employee.tz or 'UTC'),
            )]
        work_intervals = employee._get_schedule_work_intervals(query_start, query_stop, {employee: calendar_periods})
        business_hours = []
        for employee_tz, intervals in work_intervals[employee]:
            employee_tzinfo = ZoneInfo(employee_tz)
            for start, stop, _meta in intervals:
                # Resource attendances encode 24:00 as the last microsecond of the day.
                if stop.astimezone(employee_tzinfo).time() == time.max:
                    stop += timedelta(microseconds=1)
                start = max(start.astimezone(tz), start_period)
                stop = min(stop.astimezone(tz), stop_period)
                if start >= stop:
                    continue
                for day in date_range(
                    start.date(), (stop - timedelta(microseconds=1)).date(), step=timedelta(days=1),
                ):
                    day_start = datetime.combine(day, time.min, tzinfo=tz)
                    day_end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
                    seg_start, seg_stop = max(start, day_start), min(stop, day_end)
                    business_hours.append({
                        "daysOfWeek": [(day.weekday() + 1) % 7],
                        "startTime": seg_start.strftime("%H:%M"),
                        "endTime": "24:00" if seg_stop == day_end else seg_stop.strftime("%H:%M"),
                    })
        return business_hours
