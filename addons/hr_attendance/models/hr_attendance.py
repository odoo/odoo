# Part of Odoo. See LICENSE file for full copyright and licensing details.

from calendar import monthrange
from datetime import UTC, datetime, timedelta
from random import randint
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools import convert, float_compare, float_is_zero, format_datetime
from odoo.tools.date_utils import float_to_time, sum_intervals, time_to_float
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
    out_ip_address = fields.Char(readonly=True)
    out_browser = fields.Char(readonly=True)
    out_mode = fields.Selection(selection=[('kiosk', "Kiosk"),
                                           ('systray', "Systray"),
                                           ('manual', "Manual"),
                                           ('technical', 'Technical'),
                                           ('auto_check_out', 'Automatic Check-Out')],
                                readonly=True,
                                tracking=True,
                                default='manual')
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
    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', string="Time Type", index=True, required=True,
        default=lambda self: self.env.company.sudo().attendance_work_entry_type_id,
    )
    wet_display_code = fields.Char(related='work_entry_type_id.display_code', export_string_translation=False)

    state = fields.Selection([
        ('draft', 'To Review'),
        ('validated', 'Reviewed'),
        ('refused', 'Refused'),
    ], string='Status', required=True, default='draft', index=True, tracking=True, readonly=True, copy=False)
    # issues of the employee's day, see _compute_issues
    is_late_check_in = fields.Boolean(string="Late Clock In", compute="_compute_issues", store=True)
    is_early_check_out = fields.Boolean(string="Early Clock Out", compute="_compute_issues", store=True)
    is_overtime = fields.Boolean(string="Overtime", compute="_compute_issues", store=True)
    is_undertime = fields.Boolean(string="Undertime", compute="_compute_issues", store=True)
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

    @api.depends('employee_id', 'check_in', 'check_out', 'break_duration', 'time_rule_id', 'in_mode', 'out_mode')
    def _compute_issues(self):
        """Flag the late check-ins, the early check-outs, the overtimes and the undertimes, see :meth:`_get_issues`."""
        late_attendances, early_attendances, overtime_attendances, undertime_attendances = self._origin._get_issues()
        for attendance in self:
            attendance.is_late_check_in = attendance._origin in late_attendances
            attendance.is_early_check_out = attendance._origin in early_attendances
            attendance.is_overtime = attendance._origin in overtime_attendances
            attendance.is_undertime = attendance._origin in undertime_attendances

    @api.model
    def _get_worked_time_domain(self):
        """Return the domain of the attendances that count as worked time when looking for issues. The refused and
        technical attendances, and the undertime outputs of the time rules, do not count. The overtime outputs do: when
        a day is reviewed, the time rules move its extra hours to them, and without them the day would end earlier and
        look like an early check-out.
        """
        return Domain([
            ("state", "!=", "refused"),
            ("in_mode", "!=", "technical"),
        ]) & (Domain("time_rule_id", "=", False) | Domain("time_rule_id.threshold_operator", "=", "exceed"))

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
        """Return the late check-ins, the early check-outs, the overtimes and the undertimes on the days of the
        attendances in self.

        Each day of an employee is compared with the shifts of their schedule on that day, give or take the company's
        tolerance (``attendance_validation_tolerance``, in minutes).

        - The first attendance of the day is a late check-in if it starts after the first shift.
        - The last attendance of the day is an early check-out if it ends before the end of the last shift. Not while
          an attendance of the day is still open, nor when the automatic check-out closed it: the employee forgot to
          check out, and the attendance goes to review anyway, see :meth:`_get_auto_review_domain`.
        - The last attendance of the day is an overtime if the day has more worked hours than the shifts. On a day off,
          any worked hour is overtime.
        - The last attendance of the day is an undertime if the day has fewer worked hours than the shifts. Not when
          the automatic check-out closed it, for the same reason as the early check-out.

        Employees with a flexible schedule have no issue.

        :return: ``(late check-ins, early check-outs, overtimes, undertimes)``, four ``hr.attendance`` recordsets
        :rtype: tuple
        """
        late_attendances = early_attendances = overtime_attendances = undertime_attendances = self.env["hr.attendance"]
        worked_attendances = self._search_same_day_attendances(self._get_worked_time_domain())
        for employee, employee_attendances in worked_attendances.grouped("employee_id").items():
            tolerance = timedelta(minutes=employee.company_id.attendance_validation_tolerance)
            attendances_by_day = employee_attendances.grouped("date")
            shifts_by_day = employee._get_expected_attendances_by_day(attendances_by_day)
            for day, shifts in shifts_by_day.items():
                day_attendances = attendances_by_day[day]
                first_attendance = min(day_attendances, key=lambda a: a.check_in)
                if shifts and first_attendance.check_in.replace(tzinfo=UTC) > shifts[0][0] + tolerance:
                    late_attendances |= first_attendance

                if not all(day_attendances.mapped("check_out")):
                    continue
                last_attendance = max(day_attendances, key=lambda a: a.check_out)
                if (
                    shifts
                    and last_attendance.out_mode != "auto_check_out"
                    and last_attendance.check_out.replace(tzinfo=UTC) < shifts[-1][1] - tolerance
                ):
                    early_attendances |= last_attendance
                worked_time = timedelta(hours=sum(day_attendances.mapped("worked_hours")))
                expected_time = timedelta(hours=sum_intervals(shifts))
                if worked_time > expected_time + tolerance:
                    overtime_attendances |= last_attendance
                elif (
                    shifts
                    and last_attendance.out_mode != "auto_check_out"
                    and worked_time < expected_time - tolerance
                ):
                    undertime_attendances |= last_attendance
        return late_attendances, early_attendances, overtime_attendances, undertime_attendances

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

        :raise ValidationError: if the attendance overlaps another one or if another attendance
            of the employee is still open
        """
        if self.env.context.get('skip_time_rules'):
            return
        for attendance in self:
            # we take the latest attendance before our check_in time and check it doesn't overlap with ours
            last_attendance_before_check_in = self.env['hr.attendance'].search([
                ('employee_id', '=', attendance.employee_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out > attendance.check_in:
                raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s",
                                                   empl_name=attendance.employee_id.name,
                                                   datetime=format_datetime(self.env, last_attendance_before_check_in.check_in, dt_format=False)))

            if not attendance.check_out:
                # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                no_check_out_attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_out', '=', False),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if no_check_out_attendances:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee hasn't checked out since %(datetime)s",
                                                       empl_name=attendance.employee_id.name,
                                                       datetime=format_datetime(self.env, no_check_out_attendances.check_in, dt_format=False)))
            else:
                # we verify that the latest attendance with check_in time before our check_out time
                # is the same as the one before our check_in time computed before, otherwise it overlaps
                last_attendance_before_check_out = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s",
                                                       empl_name=attendance.employee_id.name,
                                                       datetime=format_datetime(self.env, last_attendance_before_check_out.check_in, dt_format=False)))

    # The fields a manager approves when reviewing an attendance. When one of them changes, the time rule outputs of
    # the attendance are out of date, the issues of its day may change, and a change by the employee needs a new review.
    _REVIEWED_FIELDS = frozenset({'check_in', 'check_out', 'break_duration', 'employee_id', 'work_entry_type_id'})

    def write(self, vals):
        """Write the values. When a reviewed field changes (``_REVIEWED_FIELDS``):

        - A check-in or check-out changed by a user becomes manual, unless the values give its mode. The devices, the
          automatic check-out and the time rules write as superuser and keep their mode.
        - If the employee changes their own attendance, it goes back to To Review. So the time rules give nothing for
          it until a manager reviews it again.
        - Otherwise, :meth:`_auto_review` may review it again.
        - The time rule outputs of the attendance are flagged as out of date (``source_stale``).
        - The issues of the days of the attendance are recomputed. The other attendances of those days that no longer
          have an issue may be reviewed by :meth:`_auto_review`.

        Refusing an attendance, or taking back its refusal, also recomputes the issues of its days, as it no longer
        counts, or counts again, as worked time.

        :raise AccessError: see :meth:`_check_write_access`
        """
        self._check_write_access(vals)
        changes_reviewed_fields = bool(self._REVIEWED_FIELDS & vals.keys())
        changes_refusal = "state" in vals and any((a.state == "refused") != (vals["state"] == "refused") for a in self)
        if not changes_reviewed_fields and not changes_refusal:
            return super().write(vals)

        edited_by_manager, edited_by_employee = self.partitioned(lambda a: self.env.su or a.is_manager)
        manual_modes = {} if self.env.su else {
            f"{side}_mode": "manual" for side in ("in", "out") if f"check_{side}" in vals
        }
        manager_vals = {**manual_modes, **vals}
        # the employee's own edit is manual whatever mode they send
        employee_vals = {**vals, **manual_modes, "state": "draft"}

        # the attendances of the days before the write, as it can move attendances to other days
        same_day_attendances_before = self._search_same_day_attendances() - self
        # the attendances the time rules created before the write (overtime and undertime): the ones they create in the
        # write are up to date
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
                self.env._(
                    "Do not have access, user cannot edit the attendances that are not their own or if they are not the attendance manager of the employee."
                )
            )
        if not all(self.mapped("is_manager")) and self._requires_attendance_manager(vals):
            raise AccessError(self.env._("Only the attendance managers of the employees can review their attendances."))

    @api.model
    def _requires_attendance_manager(self, vals):
        """Return whether only an attendance manager may write these values. That is when they review the attendance,
        when they say that it was recorded by the kiosk or the systray, or when they make it a time rule output. The
        kiosk, the systray and the time rules write as superuser.

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
        self.ensure_one()
        return self._get_check_in_out_log('in')

    def _get_check_in_out_log(self, direction):
        """Return the chatter message logged when the employee checks in or out.

        The message gives the mode (kiosk, systray, ...) and the location. When the GPS position is known, the
        location links to Google Maps. The browser and the IP address, when known, follow on a second, muted line.

        :param str direction: ``'in'`` or ``'out'``
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
        """Check out the open attendances once the hours of their day's schedule and the
        company's ``auto_check_out_tolerance`` have passed.

        Applies to the companies in ``tolerance`` mode, to employees with a non flexible schedule.
        The check-out is set at check-in + the expected hours of the attendance's day
        (``hr.employee._get_expected_attendances_by_day``) not already worked that day (at
        least one second after the check-in): the first check-in of the day + the schedule's hours
        + the breaks between the attendances. The worked hours are those of :meth:`_get_worked_time_domain`. The tolerance only delays the check-out, it adds no
        worked time. ``out_mode`` is set to ``'auto_check_out'`` and a message is posted.
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
                if attendance.date not in expected_by_day:  # flexible schedule
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
        if to_review := self.filtered_domain(self._get_auto_review_domain()):
            # as superuser: the company setting reviews them, not the user who checked out
            to_review.sudo().with_context(tracking_disable=True).write({"state": "validated"})

    @api.model
    def _get_auto_review_domain(self):
        """Return the domain of the attendances that are reviewed at check-out, without a manager."""
        return Domain([
            ("state", "=", "draft"),
            ("check_out", "!=", False),
            ("time_rule_id", "=", False),
            ("employee_id.company_id.attendance_validation", "=", "exception_validation"),
            ("in_mode", "!=", "manual"),
            ("out_mode", "not in", ("manual", "auto_check_out")),
            ("has_issue", "=", False),
        ])

    @api.model_create_multi
    def create(self, vals_list):
        """Create the attendances.

        An attendance encoded by hand by an attendance manager is Reviewed at once. The others are To Review, and
        :meth:`_auto_review` may review them. It may also review the other attendances of their days that no longer
        have an issue.

        :raise AccessError: if a user who is not an attendance manager creates a reviewed attendance or one from a
            device, see :meth:`_requires_attendance_manager`
        """
        # without an employee, an attendance gets the default one: the user's
        employee_ids = [vals.get("employee_id") or self._default_employee().id for vals in vals_list]
        employees = (
            self.env["hr.employee"].browse(vals["employee_id"] for vals in vals_list if vals.get("employee_id"))
            | self._default_employee()
        )
        managed_employee_ids = employees._filter_attendance_managed_by_current_user().ids
        for vals, employee_id in zip(vals_list, employee_ids):
            if self.env.su or employee_id in managed_employee_ids:
                if vals.get("in_mode", "manual") == "manual":
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
        """Validate the attendances, which runs the time rules on them."""
        self.write({'state': 'validated'})

    def action_refuse(self):
        """Refuse the attendances and the records the time rules created from them
        (``overtime_attendance_ids``), without running the time rules (``skip_time_rules``)."""
        (self | self.overtime_attendance_ids).with_context(skip_time_rules=True).write({'state': 'refused'})

    def action_reset_to_draft(self):
        """Set the attendances back to draft."""
        self.write({'state': 'draft'})

    @api.model
    def get_empty_list_help(self, help_message):
        """Welcome the users by their name on their empty attendances. The action's help is static,
        so the name can only come from here.
        """
        if self.env.context.get('my_attendances'):
            help_message = Markup('<p>%s</p><p>%s</p>') % (
                self.env._("Welcome %s! Log your attendances here.", self.env.user.name),
                self.env._("Check in from the top bar when you start and check out when you leave: your worked hours show up here."),
            )
        return super().get_empty_list_help(help_message)

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
        action_domain = Domain(domain or Domain.TRUE)
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
