# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL
from odoo.tools.intervals import Intervals

from odoo.addons.hr_work_entry.models.hr_time_rule import _to_utc
from odoo.addons.hr_work_entry.models.hr_time_rule_source_mixin import _to_local_date

# fields that when changed update the working time leave of the attendance
_WORKING_TIME_LEAVE_FIELDS = frozenset({'check_in', 'check_out', 'break_duration', 'employee_id', 'state'})

# the time off of the attendances follows them: no approval, no check; the time rules only run
# from the crons
_WORKING_TIME_LEAVE_CTX = {
    'skip_time_rules': True,
    'leave_fast_create': True,
    'leave_skip_date_check': True,
    'leave_skip_state_check': True,
    'skip_check_validity': True,
    'skip_leave_version_check': True,
    'tracking_disable': True,
    'mail_activity_automation_skip': True,
}


class HrAttendance(models.Model):
    """Attendances are time rule sources, evaluated on create and write when they end before
    today, else by the crons.

    Only the validated attendances of attendance based employees with a working schedule
    (not flexible) are sources. The attendances are never split: the rule outputs are written as
    validated time off linked to the attendance (``attendance_id``), see
    ``hr.time.rule._apply_attendance_output``.
    """
    _name = 'hr.attendance'
    _inherit = ['hr.attendance', 'hr.time.rule.source.mixin']

    _time_rule_span_start_field = 'check_in'
    _time_rule_span_end_field = 'check_out'

    related_leave_ids = fields.One2many('hr.leave', 'attendance_id', string="Related Time Off", readonly=True)
    related_leave_count = fields.Integer(compute='_compute_related_leave_count')

    @api.depends('related_leave_ids')
    def _compute_related_leave_count(self):
        for attendance in self:
            attendance.related_leave_count = len(attendance.related_leave_ids)

    def action_open_related_leaves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Time Off"),
            'res_model': 'hr.leave',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.related_leave_ids.ids)],
        }

    has_time_off_conflict = fields.Boolean(
        string="On Time Off", compute='_compute_has_time_off_conflict', search='_search_has_time_off_conflict',
        help="The attendance overlaps an approved time off of the employee.")

    @api.depends('employee_id', 'check_in', 'check_out')
    def _compute_has_time_off_conflict(self):
        """Flag the attendances that overlap an approved time off of the employee. An attendance that is not checked
        out yet counts until the moment it is read as the field is not stored, so it is computed again at each read.
        The time off generated from the attendances (working time, time rule outputs) is the worked time, not a time
        off.
        """
        self.has_time_off_conflict = False
        attendances = self.filtered(lambda a: a.employee_id and a.check_in)
        if not attendances:
            return
        now = fields.Datetime.now()
        leaves_by_employee = self.env['hr.leave'].sudo().search([
            ('state', '=', 'validate'),
            ('attendance_id', '=', False),
            ('employee_id', 'in', attendances.employee_id.ids),
            ('date_from', '<', max(attendances.mapped(lambda a: a.check_out or now))),
            ('date_to', '>', min(attendances.mapped('check_in'))),
        ]).grouped('employee_id')
        for attendance in attendances:
            check_out = attendance.check_out or now
            attendance.has_time_off_conflict = any(
                leave.date_from < check_out and leave.date_to > attendance.check_in
                for leave in leaves_by_employee.get(attendance.employee_id, [])
            )

    def _search_has_time_off_conflict(self, operator, value):
        if operator != 'in':
            return NotImplemented
        if True in value and False in value:
            return Domain.TRUE
        # an overlap between two tables cannot be expressed as a domain
        conflicts = SQL("""(
            SELECT attendance.id
              FROM hr_attendance attendance
              JOIN hr_leave leave
                ON leave.employee_id = attendance.employee_id
               AND leave.state = 'validate'
               AND leave.attendance_id IS NULL
               AND leave.date_from < COALESCE(attendance.check_out, NOW() AT TIME ZONE 'UTC')
               AND leave.date_to > attendance.check_in
        )""")
        return Domain('id', 'in' if True in value else 'not in', conflicts)

    @api.depends('has_time_off_conflict')
    def _compute_has_issue(self):
        """Overlapping an approved time off is an issue."""
        super()._compute_has_issue()
        self.filtered('has_time_off_conflict').has_issue = True

    @api.model_create_multi
    def create(self, vals_list):
        """Create the working time leaves of the new attendances, then run the time rules on
        their days (see :meth:`_trigger_time_rules_on_days`)."""
        attendances = super().create(vals_list)
        attendances._sync_working_time_leaves()
        if not self.env.context.get('skip_time_rules'):
            self._trigger_time_rules_on_days(attendances._get_time_rule_days())
        return attendances

    def write(self, vals):
        """Reverse the allocation credits of the attendances that are no longer reviewed, and update the time off of
        the attendances: it is deleted, time rule outputs included, and created again, then the time rules run on the
        days of the attendances, before and after the write (see :meth:`_trigger_time_rules_on_days`).

        The review state is checked after the write, because ``hr_attendance`` may change it there: an employee's
        edit sends their attendance back to To Review.

        :raise ValidationError: if the allocation was already used beyond its allowed balance
        """
        reviewed = self.filtered(lambda a: a.state == 'validated')
        sync = bool(_WORKING_TIME_LEAVE_FIELDS & vals.keys())
        days = self._get_time_rule_days() if sync else set()
        result = super().write(vals)
        if no_longer_reviewed := reviewed.filtered(lambda a: a.state != 'validated'):
            self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', no_longer_reviewed.ids)
        if sync:
            self._sync_working_time_leaves()
            if not self.env.context.get('skip_time_rules'):
                self._trigger_time_rules_on_days(days | self._get_time_rule_days())
        return result

    @api.ondelete(at_uninstall=False)
    def _reverse_credits_on_unlink(self):
        """Reverse the allocation credits logged on the deleted attendances."""
        self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', self.ids)

    @api.ondelete(at_uninstall=False)
    def _unlink_working_time_leaves(self):
        """Delete the time off of the deleted attendances: working time leaves, with their time
        rule outputs, and time rule outputs. Once they are deleted, the time rules run on their
        days, so that the other attendances of those days are evaluated without them."""
        leaves = self.env['hr.leave'].sudo().with_context(**_WORKING_TIME_LEAVE_CTX).search([('attendance_id', 'in', self.ids)])
        (leaves | leaves.output_leave_ids).unlink()
        if not self.env.context.get('skip_time_rules'):
            days = self._get_time_rule_days()
            return lambda: self.browse()._trigger_time_rules_on_days(days)

    def _get_working_time_leave_vals(self, date_from, date_to, work_entry_type):
        """Return the values of a validated time off of the attendance.

        :param datetime date_from: naive UTC
        :param datetime date_to: naive UTC
        :param work_entry_type: ``hr.work.entry.type`` of the time off
        :return: the creation values in a list, empty when the time off has no duration
        :rtype: list[dict]
        """
        self.ensure_one()
        if date_to <= date_from:
            return []
        tz = ZoneInfo(self.employee_id._get_tz())
        local_from = date_from.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        local_to = date_to.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        return [{
            'employee_id': self.employee_id.id,
            'work_entry_type_id': work_entry_type.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': local_from.date(),
            'request_date_to': local_to.date(),
            'request_hour_from': local_from.hour + local_from.minute / 60,
            'request_hour_to': local_to.hour + local_to.minute / 60,
            'attendance_id': self.id,
            'state': 'validate',
        }]

    def _sync_working_time_leaves(self):
        """Delete the time off of the attendances, time rule outputs included, with their
        allocation credits, and create again their working time leaves.

        Only validated, closed attendances of employees whose version is attendance based
        (``work_entry_source``) with a flexible schedule on that day have one: a copy of the
        attendance, from ``check_in`` to ``check_out`` minus the break, with the default type of
        the version, that the time rules split. The time rules are not run, see
        :meth:`_trigger_time_rules_on_days`.
        """
        Leave = self.env['hr.leave'].sudo().with_context(**_WORKING_TIME_LEAVE_CTX)
        # even empty, the unlink and create of time off invalidate the whole cache
        if leaves := Leave.search([('attendance_id', 'in', self.ids)]):
            leaves.unlink()
        self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', self.ids)
        vals_list = []
        for attendance in self.filtered(lambda a: a.state == 'validated' and a.check_out):
            # sudo: the employees checking in and out may not read the versions
            version = attendance.employee_id.sudo()._get_version(attendance.date)
            if version.work_entry_source == 'attendance' and version._is_flexible():
                vals_list += attendance._get_working_time_leave_vals(
                    attendance.check_in,
                    attendance.check_out - timedelta(hours=attendance.break_duration),
                    self.env['hr.work.entry.type'].browse(version._get_default_work_entry_type_id()),
                )
        if vals_list:
            Leave.create(vals_list)

    def _get_time_rule_days(self):
        """Return the days of the closed attendances.

        :return: ``(employee, first day, last day)`` tuples, the days in the employee's timezone
        :rtype: set[tuple]
        """
        return {
            (attendance.employee_id, attendance.date, _to_local_date(attendance.employee_id, attendance.check_out))
            for attendance in self.sudo()
            if attendance.check_out
        }

    @api.model
    def _trigger_time_rules_on_days(self, days):
        """Run the time rules on days of attendances, as superuser: on their working time
        leaves when the version of the employee that day is attendance based with a flexible
        schedule, else on the attendances. The days ending today or later are left to the
        crons.

        :param days: ``(employee, first day, last day)`` tuples, see :meth:`_get_time_rule_days`
        """
        today = date.today()
        by_flexible = {True: [], False: []}
        for employee, first_day, last_day in days:
            version = employee.sudo()._get_version(first_day)
            if last_day < today and version.work_entry_source == 'attendance':
                by_flexible[version._is_flexible()].append((employee, first_day, last_day))
        self.sudo()._trigger_time_rules_for_affected(by_flexible[False])
        self.env['hr.leave'].sudo()._trigger_time_rules_for_affected(by_flexible[True])

    # ------------------------------------------------------------
    # Time rules
    # ------------------------------------------------------------

    def _get_source_extra_fields_domain(self):
        """Only the validated attendances are time rule sources, see
        :meth:`_get_source_records_for_time_rules`.

        :rtype: list
        """
        return [('state', '=', 'validated')]

    def _get_source_records_for_time_rules(self, start_dt, end_dt, employees=None, check_end=False):
        """Only keep the attendances of the days the version of the employee is attendance
        based with a working schedule (not flexible)."""
        return super()._get_source_records_for_time_rules(start_dt, end_dt, employees, check_end).filtered(
            lambda a: (version := a.employee_id._get_version(a.date)).work_entry_source == 'attendance'
            and not version._is_flexible())

    def _get_pipeline_intervals_local(self, schedule):
        """The time rules see the attendance from ``check_in`` to ``check_out`` minus the break, as the time off of
        a flexible schedule: the break is at the end."""
        start, stop = super()._get_pipeline_intervals_local(schedule)[0]
        return [(start, max(start, stop - timedelta(hours=self.break_duration)))]

    def _get_write_source_extra_source_fields(self):
        """Writing ``state`` or ``break_duration`` also runs the rules.

        :rtype: set[str]
        """
        return {'state', 'break_duration'}

    def _get_time_rule_work_entry_type(self):
        """Attendances have no type: the time rules see them as Work, whatever the country (see
        ``hr.time.rule._evaluate_rules``).

        :rtype: hr.work.entry.type
        """
        return self.env.ref('hr_work_entry.generic_work_entry_type_attendance')

    def _trigger_time_rules(self):
        """Nothing: create and write run the rules once the time off of the attendances is
        synchronized, see :meth:`_trigger_time_rules_on_days`."""
        return

    def _trigger_time_rules_for_affected(self, affected):
        """Only run the rules on create and write for the attendances ending before today: the
        days still running are evaluated by :meth:`_cron_process_day_time_rules`."""
        today = date.today()
        return super()._trigger_time_rules_for_affected(
            [a for a in affected if _to_local_date(a[0], a[2]) < today])

    def _process_time_rules_for(self, affected, rule_period=None, rule_operator=None, rule_week_start=None):
        """Keep the evaluated attendances and days in the context, see :meth:`_apply_record_output`."""
        return super(HrAttendance, self.with_context(time_rule_collected_ids=set(), time_rule_windows=[]))._process_time_rules_for(
            affected, rule_period=rule_period, rule_operator=rule_operator, rule_week_start=rule_week_start,
        )

    def _collect_time_rule_outputs(self, rules, ranges_by_employee):
        """Keep the days evaluated for ``rules`` in the context, see :meth:`_apply_record_output`."""
        if (windows := self.env.context.get('time_rule_windows')) is not None:
            windows.append((rules.ids, {employee.id: tuple(dates) for employee, dates in ranges_by_employee.items()}))
        return super()._collect_time_rule_outputs(rules, ranges_by_employee)

    def _on_sources_collected(self, sources):
        """Reverse the allocation credits of the evaluated attendances, once per trigger (see
        ``hr_holidays``), and keep them for :meth:`_apply_record_output`.

        :param sources: ``hr.attendance`` records
        """
        reversed_ids = self.env.context.get('time_rule_reversed_ids')
        to_reverse = set(sources.ids)
        if reversed_ids is not None:
            to_reverse -= reversed_ids
            reversed_ids |= to_reverse
        self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', to_reverse)
        self.env.context['time_rule_collected_ids'].update(sources.ids)

    def _apply_record_output(self, rules, excess, deficit, active_iv=None):
        """Replace the time rule outputs of the evaluated attendances for ``rules``, see
        ``hr.time.rule._apply_attendance_output``. Only those of the evaluated days are replaced:
        an attendance may also overlap other days. Then the outputs of the daily rules are cut
        where the weekly rules take over their hours, see :meth:`_cut_daily_time_rule_outputs`."""
        collected_ids = self.env.context.get('time_rule_collected_ids', set())
        evaluated_days = Domain.OR(
            Domain('employee_id', '=', employee_id)
            & Domain('time_rule_id', 'in', rule_ids)
            & Domain('date_from', '>=', _to_utc(datetime.combine(date_from, time.min), tz))
            & Domain('date_from', '<', _to_utc(datetime.combine(date_to + timedelta(days=1), time.min), tz))
            for rule_ids, ranges in self.env.context.get('time_rule_windows', [])
            for employee_id, (date_from, date_to) in ranges.items()
            for tz in [ZoneInfo(self.env['hr.employee'].browse(employee_id).sudo()._get_tz())]
        )
        outputs = self.env['hr.leave'].sudo().with_context(**_WORKING_TIME_LEAVE_CTX).search(
            Domain('attendance_id', 'in', list(collected_ids))
            & Domain('time_rule_id', 'in', rules.ids)
            & evaluated_days
        )
        outputs.unlink()
        rules._apply_attendance_output(excess, deficit, active_iv=active_iv)
        self._cut_daily_time_rule_outputs(collected_ids)

    def _cut_daily_time_rule_outputs(self, attendance_ids):
        """Cut the outputs of the daily ``exceed`` rules where an output of a weekly ``exceed``
        rule of the same attendance overlaps them: the weekly rules take over these hours.

        :param attendance_ids: ids of ``hr.attendance``
        """
        Leave = self.env['hr.leave'].sudo().with_context(**_WORKING_TIME_LEAVE_CTX)
        outputs = Leave.search([
            ('attendance_id', 'in', list(attendance_ids)),
            ('time_rule_id.threshold_operator', '=', 'exceed'),
        ])
        weekly_by_attendance = outputs.filtered(lambda o: o.time_rule_id.quantity_period == 'week').grouped('attendance_id')
        if not weekly_by_attendance:
            return
        dummy = self.env['resource.calendar']
        to_unlink = Leave
        vals_list = []
        for output in outputs.filtered(lambda o: o.attendance_id in weekly_by_attendance and o.time_rule_id.quantity_period != 'week'):
            weekly = Intervals([(w.date_from, w.date_to, dummy) for w in weekly_by_attendance[output.attendance_id]])
            daily = Intervals([(output.date_from, output.date_to, dummy)])
            if not daily & weekly:
                continue
            to_unlink |= output
            rule = output.time_rule_id
            vals_list += [
                output.attendance_id._get_time_rule_output_vals(rule, start, stop, rule._get_pp_frozenset())
                for start, stop, _dummy in daily - weekly
            ]
        # even empty, the unlink and create of time off invalidate the whole cache
        if to_unlink:
            to_unlink.unlink()
            Leave.create(vals_list)

    def _get_time_rule_deficit_occupied(self, employee_id, start_utc, period_end_utc):
        """Return the spans of the attendances of the employee overlapping the period, refused
        ones excepted, so that undertime outputs are placed outside of them. As for the time
        rules, the break is at the end (:meth:`_get_pipeline_intervals_local`): the undertime of a
        break stays in the schedule, where payroll deducts it.

        :rtype: Intervals
        """
        dummy = self.env['resource.calendar']
        existing = self.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee_id),
            ('check_in', '<', period_end_utc),
            ('check_out', '>', start_utc),
            ('state', '!=', 'refused'),
        ])
        return Intervals([
            (a.check_in, max(a.check_in, a.check_out - timedelta(hours=a.break_duration)), dummy)
            for a in existing
        ], keep_distinct=True)

    def _get_time_rule_output_vals(self, rule, df, dt, pp):
        """Return the values of an output time off: the rule's type, linked to the attendance.

        :rtype: dict
        """
        vals_list = self._get_working_time_leave_vals(df, dt, rule.work_entry_type_id)
        return vals_list and {**vals_list[0], 'time_rule_id': rule.id}

    @api.model
    def _cron_process_day_time_rules(self):
        """Cron: evaluate the daily rules (both operators) on yesterday's attendances, and the
        daily ``exceed`` rules on yesterday's working time leaves of attendances (``hr_holidays``
        evaluates the ``less_than`` ones). On create and write, the rules only run for the days
        before today.
        """
        yesterday = date.today() - timedelta(days=1)
        start = datetime.combine(yesterday, time.min)
        end = datetime.combine(yesterday, time.max)
        sources = self._get_source_records_for_time_rules(start, end, check_end=True)
        self._process_time_rules_for(
            [(s.employee_id, s.check_in, s.check_out) for s in sources], rule_period='day')
        Leave = self.env['hr.leave']
        leaves = Leave._get_source_records_for_time_rules(start, end, check_end=True).filtered('attendance_id')
        Leave._process_time_rules_for(
            [(l.employee_id, l.date_from, l.date_to) for l in leaves], rule_period='day', rule_operator='exceed')
