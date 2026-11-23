# Part of Odoo. See LICENSE file for full copyright and licensing details.

from bisect import bisect_left, bisect_right
from calendar import monthrange
from datetime import UTC, datetime, time, timedelta
from random import randint
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools import convert, float_compare, float_is_zero, format_datetime, format_duration
from odoo.tools.date_utils import date_range, float_to_time, sum_intervals, time_to_float
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
    _inherit = ["mail.thread", "hr.time.rule.source.mixin"]

    _time_rule_source_field = 'source_attendance_id'
    _time_rule_output_field = 'overtime_attendance_ids'
    _time_rule_span_start_field = 'check_in'
    _time_rule_span_end_field = 'check_out'

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
    # compute_sudo: the domain is computed for every user displaying the time
    # type (e.g. My Attendances), even without read access on the time types;
    # the dropdown itself still applies the user's access rights.
    allowed_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type', compute='_compute_allowed_work_entry_type_ids', compute_sudo=True)
    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', string="Time Type", index=True, required=True,
        default=lambda self: self.env.company.sudo().attendance_work_entry_type_id,
        ui_domain="[('id', 'in', allowed_work_entry_type_ids)]",
    )
    wet_display_code = fields.Char(related='work_entry_type_id.display_code', export_string_translation=False)

    state = fields.Selection([
        ('draft', 'To Review'),
        ('validated', 'Reviewed'),
        ('refused', 'Refused'),
    ], string='Status', required=True, default='draft', index=True, tracking=True, readonly=True, copy=False)
    # issues of the employee's day, see _compute_attendance_issues
    is_late_check_in = fields.Boolean(string="Late Clock In", compute="_compute_attendance_issues", store=True)
    is_early_check_out = fields.Boolean(string="Early Clock Out", compute="_compute_attendance_issues", store=True)
    is_overtime = fields.Boolean(string="Overtime", compute="_compute_attendance_issues", store=True)
    is_undertime = fields.Boolean(string="Undertime", compute="_compute_attendance_issues", store=True)
    has_issue = fields.Boolean(
        compute="_compute_has_issue",
        export_string_translation=False,
        help="Late check-in, early check-out, overtime, undertime or another issue, flagged on the gantt view.",
    )

    # time rule engine output fields
    time_rule_id = fields.Many2one('hr.time.rule', index=True)
    source_attendance_id = fields.Many2one('hr.attendance', index=True)
    overtime_attendance_ids = fields.One2many('hr.attendance', 'source_attendance_id')
    # set to True on surviving output records when their source is modified or deleted
    source_stale = fields.Boolean(default=False, copy=False, export_string_translation=False)
    # dry run of the daily overtime rules, shown as a banner on the form
    time_rule_split_preview = fields.Html(
        compute='_compute_time_rule_split_preview', export_string_translation=False)

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

    @api.depends("employee_id", "check_in", "check_out", "work_entry_type_id", "source_stale")
    def _compute_display_name(self):
        for attendance in self:
            # employees without HR rights cannot read time types, but see them in the names of their attendances
            time_type = attendance.work_entry_type_id.sudo()
            time_type_name = time_type.display_code or time_type.name or ""
            if not attendance.check_out:
                name = time_type_name or self.env._("In Progress")
            else:
                hours, minutes = divmod(round(attendance.worked_hours * 60), 60)
                if minutes:
                    duration = self.env._("%(hours)sh %(minutes)sm", hours=hours, minutes=minutes)
                else:
                    duration = self.env._("%(hours)sh", hours=hours)
                name = f"{time_type_name} {duration}" if time_type_name else duration
            attendance.display_name = f"⚠ {name}" if attendance.source_stale else name

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

    @api.depends('employee_id.company_id.country_id')
    def _compute_allowed_work_entry_type_ids(self):
        countries = self.employee_id.company_id.country_id
        domain = self._get_work_entry_type_domain(
            country_ids=countries.ids + [False])
        # key on the country id: _read_group returns the "no country" group as
        # an empty res.country recordset, whose id is False
        types_by_country = {
            country.id: work_entry_types
            for country, work_entry_types in self.env['hr.work.entry.type']._read_group(
                domain, ['country_id'], ['id:recordset'])
        }
        generic_types = types_by_country.get(False, self.env['hr.work.entry.type'])
        for attendance in self:
            country = attendance.employee_id.company_id.country_id
            attendance.allowed_work_entry_type_ids = \
                types_by_country.get(country.id, generic_types)

    def _get_work_entry_type_domain(self, country_ids=None):
        if country_ids is None:
            country_ids = [self.employee_id.company_id.country_id.id]
        domain = [('count_as', '=', 'working_time')]
        if country_ids:
            domain.append(('country_id', 'in', country_ids))
        else:
            domain.append(('country_id', '=', False))
        return domain

    @api.depends(
        'employee_id', 'check_in', 'check_out', 'break_duration', 'work_entry_type_id', 'state',
        'time_rule_id', 'source_attendance_id', 'overtime_attendance_ids',
    )
    def _compute_time_rule_split_preview(self):
        """Show the split summary of the attendance (:meth:`_get_time_rule_split_summary`) on
        the form; empty when the rules leave the attendance as it is."""
        for attendance in self:
            summary = attendance._get_time_rule_split_summary()
            if not summary:
                attendance.time_rule_split_preview = False
            elif len(summary['parts']) == 1:
                attendance.time_rule_split_preview = Markup("<p class='mb-0'>%s.</p>") % summary['title']
            else:
                lines = Markup().join(Markup("<li>%s</li>") % part['label'] for part in summary['parts'])
                attendance.time_rule_split_preview = Markup(
                    "<p class='mb-1'>%s:</p><ul class='mb-0'>%s</ul>"
                ) % (summary['title'], lines)

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

    @api.depends('employee_id', 'check_in')
    def _compute_employee_tz(self):
        """Timezone of the employee on the check in day, for the form to warn when it differs from the browser's."""
        for attendance in self:
            if attendance.employee_id and attendance.check_in:
                # sudo() is needed because attendance officers may not have access to employee versions.
                attendance.employee_tz = attendance.employee_id.sudo()._get_version(attendance.check_in.date()).tz
            else:
                attendance.employee_tz = False

    @api.depends('employee_id', 'check_in', 'check_out', 'break_duration', 'time_rule_id', 'in_mode', 'out_mode')
    def _compute_attendance_issues(self):
        """Flag the late check-ins, the early check-outs, the overtimes and the undertimes, see :meth:`_get_issues`."""
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
        technical attendances, and the undertime outputs of the time rules, do not count. The overtime outputs do: when
        a day is reviewed, the time rules move its extra hours to them, and without them the day would end earlier and
        look like an early check-out.
        """
        return (
            Domain("state", "!=", "refused")
            & Domain("in_mode", "!=", "technical")
            & (Domain("time_rule_id", "=", False) | Domain("time_rule_id.threshold_operator", "=", "exceed"))
        )

    def _search_same_day_attendances(self, domain=Domain.TRUE):
        """Return the attendances of the same employees on the same days as ``self``, ``self`` included.

        :param domain: extra domain on the returned attendances
        :rtype: hr.attendance
        """
        return self.sudo().search(
            domain
            & Domain.OR(
                Domain("employee_id", "=", employee.id) & Domain("date", "in", attendances.mapped("date"))
                for employee, attendances in self.grouped("employee_id").items()
            ),
        )

    def _get_issues(self):
        """Find the late check-ins, the early check-outs, the overtimes and the undertimes on the days of the
        attendances in self.

        Each day of an employee is compared with the shifts of their schedule on that day, give or take the company's
        tolerance (``attendance_validation_tolerance``, in minutes). A schedule may only give hours per day, without
        times (``duration_based``): such a day has no late check-in nor early check-out, only overtime and undertime.

        - The first attendance of the day is a late check-in if it starts after the first shift.
        - The last attendance of the day is an early check-out if it ends before the end of the last shift.
        - The last attendance of the day is an overtime if the day has more worked hours than the shifts. On a day off,
          any worked hour is overtime.
        - The last attendance of the day is an undertime if the day has fewer worked hours than the shifts.

        The last three are not flagged while the employee is still at work. They are not flagged either when the
        automatic check-out closed the day, because the employee did not leave at that time. They forgot to check out,
        and the attendance goes to review for that reason, see :meth:`_get_auto_review_domain`.

        Employees with a flexible schedule have no issue.

        :return: the flagged attendances of each issue field: ``is_late_check_in``, ``is_early_check_out``,
            ``is_overtime`` and ``is_undertime``
        :rtype: dict[str, hr.attendance]
        """
        issues = dict.fromkeys(
            ("is_late_check_in", "is_early_check_out", "is_overtime", "is_undertime"), self.env["hr.attendance"],
        )
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
                worked_time = timedelta(hours=sum(day_attendances.mapped("worked_hours")))
                expected_time = timedelta(hours=sum_intervals(shifts))
                if worked_time > expected_time + tolerance:
                    issues["is_overtime"] |= last_attendance
                elif shifts and worked_time < expected_time - tolerance:
                    issues["is_undertime"] |= last_attendance
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
        for fname in ("is_late_check_in", "is_early_check_out", "is_overtime", "is_undertime"):
            self.env.add_to_compute(self._fields[fname], same_day_attendances)
        # has_issue is not stored, so add_to_compute does not reset it
        same_day_attendances.invalidate_recordset(["has_issue"])
        return had_issue

    @api.depends('is_late_check_in', 'is_early_check_out', 'is_overtime', 'is_undertime')
    def _compute_has_issue(self):
        for attendance in self:
            attendance.has_issue = (
                attendance.is_late_check_in
                or attendance.is_early_check_out
                or attendance.is_overtime
                or attendance.is_undertime
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

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """Check the attendance against the other attendances of the employee.

        An employee has at most one open attendance (without ``check_out``) and no overlapping
        attendances. Skipped when the context has ``skip_time_rules``, i.e. for the writes of
        the time rule pipeline, the refusal and the automatic check-out.

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
        # one period per group of attendances less than a day apart, so that attendances far
        # apart in time (e.g. 2024 and 2026) don't read all the attendances in between
        periods = []
        for start, stop in sorted((attendance.check_in, attendance.check_out or attendance.check_in) for attendance in self):
            if periods and start <= periods[-1][1] + timedelta(days=1):
                periods[-1][1] = max(periods[-1][1], stop)
            else:
                periods.append([start, stop])
        candidates = self.env['hr.attendance'].search_fetch(
            Domain('employee_id', 'in', self.employee_id.ids) & (
                Domain.OR(Domain('check_in', '<=', stop) & Domain('check_out', '>=', start) for start, stop in periods)
                | Domain('check_out', '=', False)
            ),
            ['employee_id', 'check_in', 'check_out'],
            order='check_in, id',
        )
        candidates_by_employee = candidates.grouped('employee_id')
        for employee, attendances in self.grouped('employee_id').items():
            employee_candidates = list(candidates_by_employee[employee])
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

    # The fields that a manager approves when reviewing an attendance. When one of them changes, the time rule outputs
    # of the attendance are out of date and the issues of its day may change. When the employee changes one of them,
    # the attendance needs a new review.
    _REVIEWED_FIELDS = frozenset({'check_in', 'check_out', 'break_duration', 'employee_id', 'work_entry_type_id'})

    def write(self, vals):
        """Write the values on the attendances, and follow up on the changes of the reviewed fields
        (``_REVIEWED_FIELDS``).

        - A check-in or check-out time changed by a user becomes encoded by hand (``manual`` mode), unless the values
          give the mode. The kiosk, the systray, the automatic check-out and the time rules write as superuser and
          keep their mode.
        - An attendance changed by its employee goes back to To Review, so the time rules ignore it until a manager
          reviews it again. An attendance changed by a manager keeps its state, and :meth:`_auto_review` may review
          it.
        - The time rule outputs of the attendance are flagged as out of date (``source_stale``).
        - The issues of the days of the attendance are recomputed, and :meth:`_auto_review` may review the other
          attendances of those days that no longer have an issue.

        Refusing an attendance, or taking back its refusal, also recomputes the issues of its days, because it stops
        or starts counting as worked time.

        :param dict vals: the values to write
        :raise AccessError: see :meth:`_check_write_access`
        """
        self._check_write_access(vals)
        changes_reviewed_fields = bool(self._REVIEWED_FIELDS & vals.keys())
        changes_refusal = "state" in vals and any((a.state == "refused") != (vals["state"] == "refused") for a in self)
        if not changes_reviewed_fields and not changes_refusal:
            return super().write(vals)

        edited_by_manager, edited_by_employee = self.partitioned(lambda a: self.env.su or a.is_manager)
        # A time changed by a user is encoded by hand. The kiosk, the systray, the automatic check-out and the time
        # rules write as superuser and keep their mode.
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
        # Only the time rule outputs created before the write are out of date, not the ones the write creates.
        stale_time_rule_attendances = (
            self.sudo().overtime_attendance_ids if changes_reviewed_fields else self.env["hr.attendance"]
        )

        super(HrAttendance, edited_by_manager).write(manager_vals)
        super(HrAttendance, edited_by_employee).write(employee_vals)

        if stale_time_rule_attendances:
            stale_time_rule_attendances.exists().with_context(skip_time_rules=True).write({"source_stale": True})
        had_issue = (same_day_attendances_before | self)._recompute_same_day_issues()

        if not self.env.context.get("skip_time_rules"):
            if "state" not in vals:
                edited_by_manager._auto_review()
            (had_issue - self)._auto_review()

        return True

    def _check_write_access(self, vals):
        """Check that the user may write the values on the attendances.

        - Only an attendance manager can give an attendance to another employee than the user.
        - Only an attendance manager can review an attendance or set its mode to a device mode, see
          :meth:`_requires_attendance_manager`.

        :raise AccessError: if the user may not write the values
        """
        if self.env.su:
            return
        if (
            vals.get("employee_id")
            and vals["employee_id"] not in self.env.user.employee_ids.ids
            and not self.env["hr.employee"].browse(vals["employee_id"])._filter_attendance_managed_by_current_user()
        ):
            raise AccessError(
                self.env._("You can only assign attendances to yourself or to the employees whose attendances you manage.")
            )
        if self._requires_attendance_manager(vals) and not all(self.mapped("is_manager")):
            raise AccessError(self.env._("Only the attendance managers of the employees can review their attendances."))

    @api.model
    def _requires_attendance_manager(self, vals):
        """Return whether only an attendance manager may write these values on an attendance.

        That is the case when the values review or refuse the attendance, give its check-in or check-out a device mode
        (kiosk, systray, ...), or make it a time rule output. The kiosk, the systray and the time rules write these
        values as superuser.

        :param dict vals: the values to write
        :rtype: bool
        """
        return (
            vals.get("state", "draft") != "draft"
            or any(vals.get(mode, "manual") != "manual" for mode in ("in_mode", "out_mode"))
            or bool(vals.get("time_rule_id") or vals.get("source_attendance_id"))
        )

    @api.ondelete(at_uninstall=False)
    def _mark_outputs_stale_on_delete(self):
        """Flag the time rule outputs of the deleted attendances with ``source_stale``."""
        outputs = self.sudo().mapped('overtime_attendance_ids').filtered('id')
        if outputs:
            outputs.with_context(skip_time_rules=True).write({'source_stale': True})

    @api.ondelete(at_uninstall=False)
    def _unlink_recompute_same_day_issues(self):
        """Recompute the issues of the other attendances on the days of the deleted attendances. The ones that no
        longer have an issue may be reviewed by :meth:`_auto_review`."""
        worked_time = self.filtered_domain(self._get_worked_time_domain())
        if same_day_attendances := worked_time._search_same_day_attendances() - self:
            return lambda: same_day_attendances._recompute_same_day_issues()._auto_review()
        return None

    def action_mark_reviewed(self):
        """Clear the ``source_stale`` flag, without re-running the time rules."""
        self.with_context(skip_time_rules=True).write({'source_stale': False})

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

    def _cron_check_attendances(self):
        """Cron: check out the forgotten open attendances, then detect yesterday's absences."""
        self._cron_auto_check_out()
        self._cron_absence_detection()

    def _cron_auto_check_out(self):
        """Cron: check out the forgotten open attendances, for the companies with
        ``auto_check_out``, in ``tolerance`` and in ``specific_time`` mode."""
        self._cron_auto_check_out_tolerance()
        self._cron_auto_check_out_specific_time()

    def _cron_auto_check_out_tolerance(self):
        """Check out the employees who forgot to, once they have worked the hours of their schedule for the day and
        the company's tolerance (``auto_check_out_tolerance``) has passed.

        This is for the companies that check out automatically after a tolerance (``auto_check_out_mode``), and for
        the employees whose schedule is not flexible. The attendance is closed at the time the employee would have
        worked the hours of their schedule for the day, counting the hours they already worked that day (see
        :meth:`_get_worked_time_domain`). The tolerance only delays the check-out, it adds no worked time. The
        check-out mode is ``auto_check_out``, and a message is posted on the attendance.
        """
        to_verify = self.search([
            ("check_out", "=", False),
            ("employee_id.company_id.auto_check_out", "=", True),
            ("employee_id.company_id.auto_check_out_mode", "=", "tolerance"),
            ("employee_id.resource_calendar_id.calendar_type", "!=", "undefined"),
        ])
        if not to_verify:
            return

        worked_hours_by_day = {
            (employee, day): worked_hours
            for employee, day, worked_hours in self._read_group(
                Domain([
                    ("employee_id", "in", to_verify.employee_id.ids),
                    ("date", "in", to_verify.mapped("date")),
                    ("check_out", "!=", False),
                ]) & self._get_worked_time_domain(),
                ["employee_id", "date:day"],
                ["worked_hours:sum"],
            )
        }

        now = fields.Datetime.now()
        for employee, attendances in to_verify.grouped("employee_id").items():
            expected_by_day = employee._get_expected_attendances_by_day(set(attendances.mapped("date")))
            tolerance = timedelta(hours=employee.company_id.auto_check_out_tolerance)
            for attendance in attendances:
                # a flexible schedule expects no hours
                if attendance.date not in expected_by_day:
                    continue
                expected_hours = sum_intervals(expected_by_day[attendance.date])
                remaining_hours = max(expected_hours - worked_hours_by_day.get((employee, attendance.date), 0), 0)
                expected_check_out = attendance.check_in + timedelta(hours=remaining_hours)
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
        """Cron: create a validated 1-second technical attendance for each employee without
        attendance yesterday.

        Only for the companies with ``absence_management``, and the employees with a schedule
        whose current version is in contract yesterday. The attendance starts at local midnight
        and has the company's attendance type, so that the daily undertime rules see the day and
        create output attendances for the missed hours. Technical attendances without any output
        are deleted afterwards.
        """
        yesterday = datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=1)
        companies = self.env['res.company'].search([('absence_management', '=', True)])
        if not companies:
            return

        checked_in_employees = self.env['hr.attendance'].search([('date', '=', yesterday)]).employee_id

        technical_attendances_vals = []
        absent_employees = self.env['hr.employee'].search([
            ('id', 'not in', checked_in_employees.ids),
            ('company_id', 'in', companies.ids),
            ('resource_calendar_id', '!=', False),
            ('current_version_id.contract_date_start', '<=', yesterday.date()),
            '|',
                ('current_version_id.contract_date_end', '=', False),
                ('current_version_id.contract_date_end', '>=', yesterday.date()),
        ])

        for emp in absent_employees:
            local_day_start = yesterday.replace(tzinfo=ZoneInfo(emp._get_tz()))
            check_in_utc = local_day_start.astimezone(UTC)
            technical_attendances_vals.append({
                'check_in': check_in_utc.strftime('%Y-%m-%d %H:%M:%S'),
                'check_out': (check_in_utc + relativedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'work_entry_type_id': emp.company_id.attendance_work_entry_type_id.id,
                'in_mode': 'technical',
                'out_mode': 'technical',
                'employee_id': emp.id,
                'state': 'validated',
            })

        technical_attendances = self.env['hr.attendance'].create(technical_attendances_vals)
        to_unlink = technical_attendances.filtered(lambda a: not a.overtime_attendance_ids)
        body = _('This attendance was automatically created to cover an unjustified absence on that day.')
        for technical_attendance in technical_attendances:
            technical_attendance.message_post(body=body)

        to_unlink.unlink()

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

    def _apply_record_output(self, rules, excess, deficit, active_iv=None):
        """Apply the time rule results through ``hr.time.rule._apply_attendance_output``."""
        rules._apply_attendance_output(excess, deficit, active_iv=active_iv)

    def _get_time_rule_deficit_occupied(self, employee_id, start_utc, period_end_utc):
        """Return the spans of the attendances of the employee overlapping the period, refused
        ones excepted, so that undertime outputs are placed outside of them.

        :rtype: Intervals
        """
        dummy = self.env['resource.calendar']
        existing = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee_id),
            ('check_in', '<', period_end_utc),
            ('check_out', '>', start_utc),
            ('state', '!=', 'refused'),
        ])
        return Intervals([(a.check_in, a.check_out, dummy) for a in existing], keep_distinct=True)

    def _get_time_rule_output_vals(self, rule, df, dt, pp):
        """Return the values of an output attendance, see
        ``hr.time.rule._get_output_attendance_vals``.

        :rtype: dict
        """
        return rule._get_output_attendance_vals(self.employee_id, df, dt, self, accumulated_pp=pp)

    def _get_time_rule_remainder_vals(self, df, dt):
        """Return the values of a remainder attendance: ``employee_id``, ``check_in``,
        ``check_out`` and ``source_attendance_id``.

        :rtype: dict
        """
        return {
            'employee_id': self.employee_id.id,
            'check_in': df,
            'check_out': dt,
            'source_attendance_id': self.id,
        }

    def _get_source_extra_fields_domain(self):
        """Only validated attendances are time rule sources.

        :rtype: list
        """
        return [('state', '=', 'validated')]

    def _get_time_rule_break_hours(self):
        """Return ``break_duration``, which the time rules do not count as worked time.

        :rtype: float
        """
        return self.break_duration or 0.0

    def _get_time_rule_split_preview(self):
        """Return the attendances the daily overtime rules would split the attendance into.

        Dry run of the ``exceed`` daily rules, nothing is written: works on unsaved (onchange)
        records and on draft ones, whatever their state. The other validated attendances of the
        employee on the same days are taken into account, as the rules evaluate the daily total;
        the saved version of the record (``_origin``) is replaced by the current values. The break
        is distributed over the parts as :meth:`hr.time.rule._apply_output` does.

        :return: ``[(work_entry_type, worked_hours)]`` in chronological order; empty when the
            attendance is not a time rule source (no span, refused, output of a rule or already
            split)
        :rtype: list
        """
        self.ensure_one()
        if (
            not (self.employee_id and self.check_in and self.check_out and self.work_entry_type_id)
            or self.check_out <= self.check_in
            or self.state == 'refused'
            or self.time_rule_id
            or self.source_attendance_id
            or self.overtime_attendance_ids
        ):
            return []
        rules = self.env['hr.time.rule'].sudo().search([
            ('active', '=', True),
            ('threshold_operator', '=', 'exceed'),
            ('quantity_period', '!=', 'week'),
            '|',
                ('company_id', '=', False),
                ('company_id', 'in', self.env.companies.ids),
        ])
        source = self.sudo()
        source_wet = self.work_entry_type_id
        break_hours = self.break_duration or 0.0
        span_secs = (self.check_out - self.check_in).total_seconds()
        if not rules:
            return [(source_wet, span_secs / 3600 - break_hours)]

        tz = ZoneInfo(self.employee_id.sudo()._get_tz())

        def to_local(dt):
            return dt.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)

        def utc_secs(start, stop):
            return (stop.replace(tzinfo=tz).astimezone(UTC) - start.replace(tzinfo=tz).astimezone(UTC)).total_seconds()

        start_local, stop_local = to_local(self.check_in), to_local(self.check_out)
        date_from, date_to = start_local.date(), stop_local.date()
        others = self._get_source_records_for_time_rules(
            datetime.combine(date_from, time.min, tzinfo=tz).astimezone(UTC),
            datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=tz).astimezone(UTC),
            self.employee_id,
        ) - self._origin
        excess, _deficit, _active_iv = rules._evaluate_rules(
            others | source, datetime.combine(date_from, time.min), datetime.combine(date_to, time.min),
        )
        outputs = [
            iv for iv in self.env['hr.time.rule']._resolve_output_intervals(
                excess.get(source.employee_id, {}).get(source, []))
            if iv.rule.work_entry_type_id
        ]
        if not outputs:
            return [(source_wet, span_secs / 3600 - break_hours)]

        # (start, stop, work entry type, keeps the source type and premium pays)
        segments = [(iv.start, iv.end, iv.wet, iv.wet == source_wet and not iv.pp) for iv in outputs]
        dummy = self.env['resource.calendar']
        outputs_iv = Intervals([(iv.start, iv.end, dummy) for iv in outputs], keep_distinct=True)
        segments += [
            (start, stop, source_wet, True)
            for start, stop, _dummy in Intervals([(start_local, stop_local, dummy)]) - outputs_iv
            if utc_secs(start, stop) >= 1
        ]
        segments.sort(key=lambda segment: segment[0])

        # the break goes to the parts keeping the source type, if they can hold it
        pool_secs = sum(utc_secs(start, stop) for start, stop, _wet, keeps_type in segments if keeps_type)
        if pool_secs < break_hours * 3600:
            pool_secs = 0
        base_secs = pool_secs or span_secs
        result = []
        for start, stop, wet, keeps_type in segments:
            secs = utc_secs(start, stop)
            part_break = secs / base_secs * break_hours if break_hours and (keeps_type or not pool_secs) else 0.0
            result.append((wet, secs / 3600 - part_break))
        return result

    def _log_time_rule_split(self, new_records, previous_values):
        """Log in the chatter of each attendance of ``self`` how the time rules split it
        (:meth:`_get_time_rule_split_summary`), with a link to each part.

        Called after the rules wrote their excess results. Attendances the rules left
        unchanged (same type, rule and check-out, no new record) get no message, so re-running
        the rules does not log twice.

        :param new_records: ``hr.attendance`` records created by the rules (or ``None``)
        :param dict previous_values: ``{attendance: (work_entry_type_id, time_rule_id,
            check_out)}`` before the rules ran
        """
        created_sources = (new_records or self.browse()).source_attendance_id
        for source in self:
            current = (source.work_entry_type_id, source.time_rule_id, source.check_out)
            if source not in created_sources and previous_values.get(source) == current:
                continue
            summary = source._get_time_rule_split_summary()
            if not summary:
                continue
            parts = self.browse([part['attendance_id'] for part in summary['parts']])
            title = self.env._(
                "%(summary)s by the time rules (%(rules)s)",
                summary=summary['title'],
                rules=', '.join(parts.time_rule_id.mapped('name')),
            )
            if len(parts) == 1:
                body = Markup("<p>%s.</p>") % title
            else:
                lines = Markup().join(
                    Markup("<li>%s</li>") % self.browse(part['attendance_id'])._get_html_link(title=part['label'])
                    for part in summary['parts']
                )
                body = Markup("<p>%s:</p><ul>%s</ul>") % (title, lines)
            source._message_log(body=body)

    def _get_time_rule_split_summary(self):
        """Return what the time rules made, or will make, of the attendance.

        The single source of the split shown by the form banner, the systray and the kiosk
        after a check-out, and the chatter. ``self`` may be any part of a split (the source or a
        record created from it): the summary is about the source.

        - Already split (records created from the source, or the source reclassified by a
          rule): the parts are the source and the records created from it, undertime records
          excepted.
        - Otherwise (unsaved, draft, or not split yet): the parts come from the dry run
          :meth:`_get_time_rule_split_preview`.

        :return: ``False`` when the rules leave the attendance as it is (or it is refused),
            else a dict with ``pending`` (``True`` when the split is not done yet), ``title``,
            ``parts`` (chronological ``[{'work_entry_type': str, 'hours': float, 'label': str,
            'attendance_id': int or False}]``, the id only for parts already created) and
            ``message`` (title and parts on one line)
        :rtype: dict | bool
        """
        self.ensure_one()
        source = (self.source_attendance_id or self).sudo()
        if source.state == 'refused':
            return False
        outputs = source.overtime_attendance_ids.filtered(
            lambda att: att.time_rule_id.threshold_operator != 'less_than'
        )
        if outputs or source.time_rule_id:
            pending = False
            split = [
                (part.work_entry_type_id, part.worked_hours, part.id)
                for part in (source | outputs).sorted('check_in')
            ]
        else:
            pending = True
            split = [(wet, hours, False) for wet, hours in source._get_time_rule_split_preview()]
            if not split or (len(split) == 1 and split[0][0] == source.work_entry_type_id):
                return False

        # the plain name: the display name of a time type depends on the viewer's companies
        # (hr_holidays adds the country), the summary must not
        if len(split) == 1:
            type_name = split[0][0].name
            if pending:
                title = self.env._("This attendance will be entirely replaced with %(type)s", type=type_name)
            else:
                title = self.env._("This attendance was entirely replaced with %(type)s", type=type_name)
        elif pending:
            title = self.env._("This attendance will be split into %(count)s attendances", count=len(split))
        else:
            title = self.env._("This attendance was split into %(count)s attendances", count=len(split))
        parts = [{
            'work_entry_type': wet.name,
            'hours': hours,
            'label': self.env._("%(type)s: %(hours)s", type=wet.name, hours=format_duration(hours)),
            'attendance_id': attendance_id,
        } for wet, hours, attendance_id in split]
        return {
            'pending': pending,
            'title': title,
            'parts': parts,
            'message': f"{title} ({', '.join(part['label'] for part in parts)})",
        }

    def _get_write_source_extra_source_fields(self):
        """Writing ``work_entry_type_id``, ``state`` or ``break_duration`` also runs the rules.

        :rtype: set[str]
        """
        return {'work_entry_type_id', 'state', 'break_duration'}

    def _auto_review(self):
        """Mark as Reviewed the attendances that a manager does not need to look at.

        That is only for the companies that review the exceptions only (``attendance_validation``). There, an
        attendance is reviewed at check-out, unless it has an issue, one of its times was encoded by hand, or the
        employee forgot to check out (automatic check-out).
        Reviewing an attendance runs the time rules on it.
        """
        if to_review := self._filter_auto_reviewable():
            # The company's setting reviews them, not the user who checked out, so this runs as superuser.
            to_review.sudo().with_context(tracking_disable=True).write({"state": "validated"})

    def _filter_auto_reviewable(self):
        """Return the attendances that are reviewed at check-out, without a manager."""
        return self.filtered_domain([
            ("state", "=", "draft"),
            ("check_out", "!=", False),
            ("time_rule_id", "=", False),
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
        attendances of their days, so those may be reviewed too.

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
        # the new attendances change the issues of the other attendances of their days
        had_issue = attendances.filtered_domain(self._get_worked_time_domain())._recompute_same_day_issues()
        (attendances | had_issue)._auto_review()
        return attendances

    def action_validate(self):
        """Validate the attendances, which runs the time rules on them. The attendances the user may not review, and
        the open ones, are skipped: a selection in the list can hold the user's own attendances, and an open
        attendance is reviewed once checked out."""
        self._filter_reviewable().filtered("check_out").write({'state': 'validated'})

    def action_refuse(self):
        """Refuse the attendances and the records the time rules created from them
        (``overtime_attendance_ids``), without running the time rules (``skip_time_rules``). The attendances the
        user may not review are skipped."""
        attendances = self._filter_reviewable()
        (attendances | attendances.overtime_attendance_ids).with_context(skip_time_rules=True).write({'state': 'refused'})

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
            'overtime': [('is_overtime', '=', True)],
            'undertime': [('is_undertime', '=', True)],
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
