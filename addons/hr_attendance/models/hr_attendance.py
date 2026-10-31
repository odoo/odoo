# Part of Odoo. See LICENSE file for full copyright and licensing details.

from calendar import monthrange
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from random import randint
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import convert, float_compare, float_is_zero, format_datetime
from odoo.tools.date_utils import float_to_time, sum_intervals, time_to_float
from odoo.tools.intervals import Intervals


def get_google_maps_url(latitude, longitude):
    return "https://maps.google.com?q=%s,%s" % (latitude, longitude)


# color index of each review state, shared by the calendar and gantt views
_STATE_COLORS = {'draft': 2, 'validated': 10, 'refused': 1}


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
    # review exceptions of the employee's day, see _compute_review_exceptions
    is_late_check_in = fields.Boolean(string="Late Check-In", compute='_compute_review_exceptions', store=True)
    is_early_check_out = fields.Boolean(string="Early Check-Out", compute='_compute_review_exceptions', store=True)
    is_overtime = fields.Boolean(string="Overtime", compute='_compute_review_exceptions', store=True)
    has_issue = fields.Boolean(
        compute='_compute_has_issue', export_string_translation=False,
        help="Late check-in, early check-out, overtime or another issue, flagged on the gantt view.")

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

    @api.depends('employee_id', 'check_in', 'check_out', 'work_entry_type_id', 'source_stale')
    def _compute_display_name(self):
        for attendance in self:
            # employees without HR rights cannot read time types, but see them in the names of their attendances
            wet = attendance.work_entry_type_id.sudo()
            wet_name = wet.display_code or wet.name or ''
            if not attendance.check_out:
                name = wet_name or _("In Progress")
            else:
                total_mins = round(attendance.worked_hours * 60)
                h, m = divmod(total_mins, 60)
                dur = f"{h}h {m}m" if m else f"{h}h"
                name = f"{wet_name} {dur}" if wet_name else dur
            attendance.display_name = f"⚠ {name}" if attendance.source_stale else name

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_is_manager(self):
        have_manager_right = self.env.user.has_group('hr_attendance.group_hr_attendance_user')
        have_officer_right = self.env.user.has_group('hr_attendance.group_hr_attendance_officer')
        have_own_right = self.env.user.has_group('hr_attendance.group_hr_attendance_own')
        for attendance in self:
            attendance.is_manager = have_manager_right or \
                (have_officer_right and attendance.attendance_manager_id.id == self.env.user.id)
            attendance.is_own = have_own_right and attendance.employee_id.user_id == self.env.user

    @api.depends('is_manager', 'is_own')
    def _compute_can_edit(self):
        for attendance in self:
            attendance.can_edit = attendance.is_manager or attendance.is_own

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

    @api.depends('employee_id', 'check_in', 'check_out', 'break_duration', 'time_rule_id', 'in_mode')
    def _compute_review_exceptions(self):
        """Flag the late check-in, the early check-out and the overtime of the employee's day.

        See :meth:`_get_review_exceptions`. Only saved attendances that count as worked
        time are flagged: not the time rule outputs, the technical and the refused attendances.
        Only refusing an attendance or bringing it back changes the exceptions of its day, so
        :meth:`write` recomputes them then, not on every review.
        """
        days = {
            attendance: (attendance.employee_id.id, attendance.date)
            for attendance in self
            if attendance.id and attendance._is_review_exception_source()
        }
        day_exceptions = self._get_review_exceptions(set(days.values()))
        no_exception = (self.browse(),) * 3
        for attendance in self:
            late, early, overtime = day_exceptions.get(days.get(attendance), no_exception)
            attendance.is_late_check_in = attendance == late
            attendance.is_early_check_out = attendance == early
            attendance.is_overtime = attendance == overtime

    def _is_review_exception_source(self):
        """Return whether the attendance counts in the review exceptions of its day.

        :rtype: bool
        """
        self.ensure_one()
        return bool(
            self.employee_id and self.check_in
            and self.state != 'refused' and not self.time_rule_id and self.in_mode != 'technical'
        )

    @api.model
    def _get_review_exceptions(self, employee_days):
        """Return the attendances of employees' days that are late, early or overtime.

        The attendances of each day are compared with the expected hours of the employee's
        schedule, with the company's ``attendance_validation_tolerance`` (minutes): the first
        attendance is late when it starts after the first expected hour, the last one is early
        when the day is closed before the last expected hour, and it is overtime when the hours
        worked that day exceed the expected ones (any hour worked on a day without expected
        hours). Flexible schedules have no exception.

        :param set employee_days: ``{(employee id, local day of the employee)}``
        :return: ``{(employee id, day): (late, early, overtime)}``, each an ``hr.attendance``
            record or empty; the days without attendance or schedule are left out
        :rtype: dict
        """
        if not employee_days:
            return {}
        attendances_by_day = self.sudo().search([
            ('employee_id', 'in', list({employee_id for employee_id, _day in employee_days})),
            ('date', 'in', list({day for _employee_id, day in employee_days})),
        ]).filtered(
            lambda a: (a.employee_id.id, a.date) in employee_days and a._is_review_exception_source()
        ).grouped(lambda a: (a.employee_id.id, a.date))
        days_by_employee = defaultdict(list)
        for employee_id, day in attendances_by_day:
            days_by_employee[employee_id].append(day)

        no_attendance = self.browse()
        exceptions = {}
        for employee in self.env['hr.employee'].sudo().browse(days_by_employee):
            tolerance = timedelta(minutes=employee.company_id.attendance_validation_tolerance)
            expected_by_day = self._get_expected_attendances_by_day(employee, days_by_employee[employee.id])
            for day, expected in expected_by_day.items():
                attendances = attendances_by_day[employee.id, day]
                expected_starts = [start for start, _stop, _att in expected]
                expected_stops = [stop for _start, stop, _att in expected]

                late = no_attendance
                first = min(attendances, key=lambda a: a.check_in)
                if expected_starts and first.check_in.replace(tzinfo=UTC) > min(expected_starts) + tolerance:
                    late = first

                early = overtime = no_attendance
                closed = attendances.filtered('check_out')
                if closed:
                    last = max(closed, key=lambda a: a.check_out)
                    if (
                        closed == attendances and expected_stops
                        and last.check_out.replace(tzinfo=UTC) < max(expected_stops) - tolerance
                    ):
                        early = last
                    worked = timedelta(hours=sum(closed.mapped('worked_hours')))
                    if worked > timedelta(hours=sum_intervals(expected)) + tolerance:
                        overtime = last
                exceptions[employee.id, day] = (late, early, overtime)
        return exceptions

    @api.model
    def _get_expected_attendances_by_day(self, employee, days):
        """Return the expected attendances of an employee on each day with a schedule that is
        not flexible, see ``hr.employee._get_expected_attendances``.

        One computation covers the days of a same timezone, as long as the result is the one of
        each day apart: the days in contract, or out of contract when the period has no contract
        (the current schedule applies then).

        :param employee: ``hr.employee`` record, in sudo
        :param list days: local days of the employee
        :return: ``{day: [(start, stop, resource.calendar.attendance)]}``, the intervals cut at
            the bounds of the day
        :rtype: dict
        """
        days_by_tz_and_contract = defaultdict(list)
        for day in days:
            version = employee._get_version(day)
            if not version.resource_calendar_id or version._is_flexible():
                continue
            in_contract = bool(employee._get_versions_with_contract_overlap_with_period(day, day))
            days_by_tz_and_contract[employee._get_tz(day), in_contract].append(day)

        expected_by_day = {day: [] for tz_days in days_by_tz_and_contract.values() for day in tz_days}
        for (tz_name, in_contract), tz_days in days_by_tz_and_contract.items():
            tz = ZoneInfo(tz_name)
            first, last = min(tz_days), max(tz_days)
            if in_contract or not employee._get_versions_with_contract_overlap_with_period(first, last):
                periods = [(first, last)]
            else:
                periods = [(day, day) for day in tz_days]
            for first, last in periods:
                expected = employee._get_expected_attendances(
                    datetime.combine(first, time.min, tz),
                    datetime.combine(last, time.max, tz),
                )
                for start, stop, calendar_attendance in expected:
                    while start < stop:
                        day = start.astimezone(tz).date()
                        if day in expected_by_day:
                            expected_by_day[day].append(
                                (start, min(stop, datetime.combine(day, time.max, tz)), calendar_attendance))
                        start = datetime.combine(day + timedelta(days=1), time.min, tz)
        return expected_by_day

    def _get_review_exception_siblings(self):
        """Return the other attendances of the employees' days of ``self``.

        :rtype: hr.attendance
        """
        days = {(attendance.employee_id.id, attendance.date) for attendance in self if attendance.date}
        if not days:
            return self.browse()
        return self.sudo().search([
            ('employee_id', 'in', list({employee_id for employee_id, _day in days})),
            ('date', 'in', list({day for _employee_id, day in days})),
        ]).filtered(lambda a: (a.employee_id.id, a.date) in days) - self

    def _recompute_review_exceptions(self):
        """Mark the review exceptions of ``self`` to recompute, after a change of their day."""
        for fname in ('is_late_check_in', 'is_early_check_out', 'is_overtime'):
            self.env.add_to_compute(self._fields[fname], self)

    @api.depends('is_late_check_in', 'is_early_check_out', 'is_overtime')
    def _compute_has_issue(self):
        for attendance in self:
            attendance.has_issue = attendance._has_issue()

    def _has_issue(self):
        """Return whether the attendance has an issue: late check-in, early check-out or
        overtime. Override to add issues.

        :rtype: bool
        """
        self.ensure_one()
        return self.is_late_check_in or self.is_early_check_out or self.is_overtime

    def _has_review_exception(self):
        """Return whether the closed attendance needs a review when its company reviews the
        exceptions only: encoded manually (not from a kiosk or the systray), or with an issue
        (:meth:`_has_issue`).

        :rtype: bool
        """
        self.ensure_one()
        return self.in_mode == 'manual' or self.out_mode == 'manual' or self._has_issue()

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

    # fields whose change on a source attendance should warn surviving outputs
    _STALE_TRIGGER_FIELDS = frozenset({'check_in', 'check_out', 'break_duration', 'employee_id', 'work_entry_type_id'})
    # fields whose change moves the review exceptions of the attendance's day
    _REVIEW_EXCEPTION_FIELDS = frozenset({'check_in', 'check_out', 'break_duration', 'employee_id'})

    def write(self, vals):
        """Write ``vals``, then flag the time rule outputs and update the review state.

        Moving an attendance to another employee requires being that employee, an attendance
        administrator or the employee's attendance approver; writing ``state`` requires managing
        the attendances. When a field of ``_STALE_TRIGGER_FIELDS`` changes, the outputs that
        existed before the write (and that survive it) get ``source_stale = True``.

        When a user who does not manage the attendance changes its check-in, check-out or
        break by hand (without a kiosk or systray mode), it goes back to To Review and the
        changed check-in/check-out mode becomes ``manual``. Otherwise a change of the times
        (without ``state``) re-applies the review policy (:meth:`_update_review_state`).

        :raise AccessError: if the user cannot assign the attendance to ``employee_id`` or
            cannot review it
        """
        if vals.get('employee_id') and \
            vals['employee_id'] not in self.env.user.employee_ids.ids and \
            not self.env.user.has_group('hr_attendance.group_hr_attendance_manager') and \
            self.env['hr.employee'].sudo().browse(vals['employee_id']).attendance_manager_id.id != self.env.user.id:
            raise AccessError(_("Do not have access, user cannot edit the attendances that are not their own or if they are not the attendance manager of the employee."))
        if 'state' in vals and not self.env.su and not all(self.mapped('is_manager')):
            raise AccessError(_("Only the attendance managers of the employees can review their attendances."))
        manual_vals = {}
        if 'check_in' in vals and 'in_mode' not in vals:
            manual_vals['in_mode'] = 'manual'
        if 'check_out' in vals and 'out_mode' not in vals:
            manual_vals['out_mode'] = 'manual'
        manually_edited = self.browse()
        if (manual_vals or 'break_duration' in vals) and 'state' not in vals and not self.env.su:
            manually_edited = self.filtered(lambda a: not a.is_manager)
        refusal_changed = self.browse()
        if 'state' in vals:
            refusal_changed = self.filtered(lambda a: (a.state == 'refused') != (vals['state'] == 'refused'))
        moves_exceptions = bool(self._REVIEW_EXCEPTION_FIELDS & vals.keys() or refusal_changed)
        exception_siblings = self.browse()
        if moves_exceptions:
            exception_siblings = self._get_review_exception_siblings()
        # snapshot existing output ids before the pipeline runs so that newly
        # created outputs (fresh, accurate) are not incorrectly marked stale
        stale_targets = self.env['hr.attendance']
        if self._STALE_TRIGGER_FIELDS & vals.keys():
            stale_targets = self.sudo().mapped('overtime_attendance_ids').filtered('id')
        result = super().write(vals)
        if stale_targets:
            stale_targets.exists().with_context(skip_time_rules=True).write({'source_stale': True})
        if moves_exceptions:
            (exception_siblings | refusal_changed | self._get_review_exception_siblings())._recompute_review_exceptions()
        if vals.get('check_out') and vals.get('out_mode') in ('kiosk', 'systray'):
            self._message_log_batch({
                attendance.id: attendance._get_check_in_out_log('out') for attendance in self
            })
        if manually_edited:
            # the user may edit their own reviewed attendance, it is then reviewed again
            manually_edited.sudo().write({**manual_vals, 'state': 'draft'})
        if (
            self._STALE_TRIGGER_FIELDS & vals.keys() and 'state' not in vals
            and not self.env.context.get('skip_time_rules')
        ):
            (self - manually_edited)._update_review_state()
        return result

    @api.ondelete(at_uninstall=False)
    def _mark_outputs_stale_on_delete(self):
        """Flag the time rule outputs of the deleted attendances with ``source_stale``."""
        outputs = self.sudo().mapped('overtime_attendance_ids').filtered('id')
        if outputs:
            outputs.with_context(skip_time_rules=True).write({'source_stale': True})

    @api.ondelete(at_uninstall=False)
    def _unlink_recompute_review_exceptions(self):
        """Recompute the review exceptions of the days of the deleted attendances, once deleted."""
        sources = self.filtered(lambda a: a._is_review_exception_source())
        if exception_siblings := sources._get_review_exception_siblings():
            return lambda: exception_siblings.exists()._recompute_review_exceptions()
        return None

    def action_mark_reviewed(self):
        """Clear the ``source_stale`` flag, without re-running the time rules."""
        self.with_context(skip_time_rules=True).write({'source_stale': False})

    def copy(self, default=None):
        raise exceptions.UserError(_('You cannot duplicate an attendance.'))

    def _creation_message(self):
        return self._get_check_in_out_log('in')

    def _get_check_in_out_log(self, direction):
        """Return the chatter message of the check-in or check-out of the attendance: its mode
        and its location, linked to Google Maps when the GPS coordinates are known.

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
                return self.env._("Check in from %(location)s (%(mode)s)", location=location, mode=mode)
            return self.env._("Check in (%(mode)s)", mode=mode)
        if location:
            return self.env._("Check out from %(location)s (%(mode)s)", location=location, mode=mode)
        return self.env._("Check out (%(mode)s)", mode=mode)

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
        The check-out is set at check-in + the expected hours of the schedule on the local day of
        the check-in (``hr.employee._get_expected_attendances``) not already worked that day (at
        least one second after the check-in): the first check-in of the day + the schedule's hours
        + the breaks between the attendances. The tolerance only delays the check-out, it adds no
        worked time. ``out_mode`` is set to ``'auto_check_out'`` and a message is posted.
        """
        def check_in_tz(attendance):
            """Returns check-in time in calendar's timezone."""
            return attendance.check_in.astimezone(ZoneInfo(attendance.employee_id._get_tz(attendance.date)))

        to_verify = self.env['hr.attendance'].search(
            [('check_out', '=', False),
             ('employee_id.company_id.auto_check_out', '=', True),
             ('employee_id.company_id.auto_check_out_mode', '=', 'tolerance'),
             ('employee_id.resource_calendar_id.calendar_type', '!=', 'undefined')]
        )

        if not to_verify:
            return

        to_verify_min_date = min(to_verify.mapped('check_in')).replace(hour=0, minute=0, second=0)
        previous_attendances = self.env['hr.attendance'].search([
                    ('employee_id', 'in', to_verify.mapped('employee_id').ids),
                    ('check_in', '>', to_verify_min_date),
                    ('check_out', '!=', False)
        ])

        mapped_previous_duration = defaultdict(lambda: defaultdict(float))
        for previous in previous_attendances:
            mapped_previous_duration[previous.employee_id][check_in_tz(previous).date()] += previous.worked_hours

        now = fields.Datetime.now()
        for att in to_verify:
            check_in_datetime = check_in_tz(att)
            check_in_day_start = check_in_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            expected_worked_hours = sum_intervals(
                att.employee_id._get_expected_attendances(
                    check_in_day_start,
                    check_in_day_start + timedelta(days=1),
                )
            )
            remaining_hours = max(expected_worked_hours - mapped_previous_duration[att.employee_id][check_in_datetime.date()], 0)
            check_out = att.check_in + timedelta(hours=remaining_hours)
            if now <= check_out + timedelta(hours=att.employee_id.company_id.auto_check_out_tolerance):
                continue
            att.write({
                'check_out': max(check_out, att.check_in + relativedelta(seconds=1)),
                'out_mode': 'auto_check_out',
            })
            att.message_post(
                body=_('This attendance was automatically checked out because the employee exceeded the allowed time for their scheduled work hours.')
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

    def _update_review_state(self):
        """Review the closed attendances To Review without exception (:meth:`_has_review_exception`),
        for the companies reviewing the exceptions only (``attendance_validation =
        'tolerance_validation'``). Time rule outputs are left aside. As for
        :meth:`action_validate`, writing the state runs the time rules on them.
        """
        to_validate = self.filtered(lambda a: (
            a.state == 'draft' and a.check_out and not a.time_rule_id
            and (a.employee_id.company_id or self.env.company).attendance_validation == 'tolerance_validation'
            and not a._has_review_exception()
        ))
        if to_validate:
            # the policy reviews them, whoever checked out
            to_validate.sudo().with_context(tracking_disable=True).write({'state': 'validated'})

    @api.model_create_multi
    def create(self, vals_list):
        """Create attendances, with an initial ``state`` derived from the review policy.

        Without ``state`` in the values, time rule outputs (``time_rule_id`` or
        ``source_attendance_id`` set) and the attendances encoded by hand by a user managing the
        employee's attendances are ``validated``; the others are ``draft`` (To Review), and
        :meth:`_update_review_state` then applies the review policy of their company.
        """
        user = self.env.user
        is_administrator = self.env.su or user.has_group('hr_attendance.group_hr_attendance_user')
        is_officer = user.has_group('hr_attendance.group_hr_attendance_officer')
        for vals in vals_list:
            if 'state' not in vals:
                if vals.get('time_rule_id') or vals.get('source_attendance_id'):
                    # system-generated outputs always auto-validate
                    vals['state'] = 'validated'
                elif vals.get('in_mode', 'manual') == 'manual' and (is_administrator or is_officer and (
                    self.env['hr.employee'].sudo().browse(vals.get('employee_id')) or user.employee_id
                ).attendance_manager_id == user):
                    vals['state'] = 'validated'
                else:
                    vals['state'] = 'draft'
        res = super().create(vals_list)
        sources = res.filtered(lambda a: a._is_review_exception_source())
        sources._get_review_exception_siblings()._recompute_review_exceptions()
        res._update_review_state()
        return res

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
    def get_attendance_dashboard_data(self):
        """Return the counters shown above the attendance lists, among the attendances the user
        can read. The domains match the filters of the search views.

        :return: ``{counter: number of attendances}``
        :rtype: dict
        """
        domains = {
            'to_review': [('state', '=', 'draft'), ('check_out', '!=', False)],
            'late_check_in': [('is_late_check_in', '=', True)],
            'early_check_out': [('is_early_check_out', '=', True)],
            'overtime': [('is_overtime', '=', True)],
            'at_work': [('check_out', '=', False)],
        }
        return {counter: self.search_count(domain) for counter, domain in domains.items()}

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
        attendances, the check in/out panel of the systray for the others when they may check
        in from Odoo, else their attendances.

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
