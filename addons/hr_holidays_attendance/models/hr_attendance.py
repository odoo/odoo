# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.intervals import Intervals

from odoo.addons.hr_work_entry.models.hr_time_rule_source_mixin import _to_local_date

# states in which an attendance no longer counts as valid source material
_INVALID_STATES = frozenset({'refused', 'draft'})

# fields that when changed update the working time leave of the attendance
_WORKING_TIME_LEAVE_FIELDS = frozenset({'check_in', 'check_out', 'break_duration', 'employee_id', 'work_entry_type_id', 'state'})

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

    Only the validated attendances of ``attendance_based`` employees with a working schedule
    (not flexible) are sources. The attendances are never split: the rule outputs are written as
    validated time off linked to the attendance (``attendance_id``), see
    ``hr.time.rule._apply_attendance_output``.
    """
    _name = 'hr.attendance'
    _inherit = ['hr.attendance', 'hr.time.rule.source.mixin']

    _time_rule_span_start_field = 'check_in'
    _time_rule_span_end_field = 'check_out'

    time_rule_leave_ids = fields.One2many(
        'hr.leave', 'attendance_id', domain=[('time_rule_id', '!=', False)],
        string="Rules Outputs", readonly=True)

    def _get_work_entry_type_domain(self, country_ids=None):
        return super()._get_work_entry_type_domain(country_ids=country_ids) + [('requires_allocation', '=', False)]

    @api.model_create_multi
    def create(self, vals_list):
        """Create the working time leaves of the new attendances."""
        attendances = super().create(vals_list)
        attendances._sync_working_time_leaves()
        return attendances

    def write(self, vals):
        """Reverse the allocation credits logged on the attendances when a validated attendance
        goes back to ``draft`` or is ``refused``, and update the working time leaves.

        :raise ValidationError: if the allocation was already used beyond its allowed balance
        """
        if vals.get('state') in _INVALID_STATES:
            to_reverse = self.filtered(lambda a: a.state == 'validated').ids
            self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', to_reverse)
        result = super().write(vals)
        if _WORKING_TIME_LEAVE_FIELDS & vals.keys():
            self._sync_working_time_leaves()
        return result

    @api.ondelete(at_uninstall=False)
    def _reverse_credits_on_unlink(self):
        """Reverse the allocation credits logged on the deleted attendances."""
        self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', self.ids)

    @api.ondelete(at_uninstall=False)
    def _unlink_working_time_leaves(self):
        """Delete the time off of the deleted attendances: working time leaves, with their time
        rule outputs, and time rule outputs."""
        leaves = self.env['hr.leave'].sudo().with_context(**_WORKING_TIME_LEAVE_CTX).search([('attendance_id', 'in', self.ids)])
        (leaves | leaves.output_leave_ids).unlink()

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
        """Create again the working time leaves of the attendances.

        Only validated, closed attendances of employees whose version is ``attendance_based``
        with a flexible schedule on that day have one: a copy of the attendance, from
        ``check_in`` to ``check_out`` minus the break, with its type, that the time rules
        split: right away when it ends before today, else from the crons. The time rule outputs
        of the attendances no longer validated are deleted.
        """
        Leave = self.env['hr.leave'].sudo().with_context(**_WORKING_TIME_LEAVE_CTX)
        invalid = self.filtered(lambda a: a.state != 'validated')
        leaves = Leave.search([('attendance_id', 'in', self.ids)]).filtered(
            lambda leave: not leave.time_rule_id or leave.attendance_id in invalid)
        (leaves | leaves.output_leave_ids).unlink()
        vals_list = []
        for attendance in self - invalid:
            if not attendance.check_out:
                continue
            version = attendance.employee_id._get_version(attendance.check_in.date())
            if version.attendance_based and version._is_flexible():
                vals_list += attendance._get_working_time_leave_vals(
                    attendance.check_in,
                    attendance.check_out - timedelta(hours=attendance.break_duration),
                    attendance.work_entry_type_id,
                )
        today = date.today()
        leaves = Leave.create(vals_list)
        leaves._trigger_time_rules_for_affected([
            (leave.employee_id, leave.date_from, leave.date_to)
            for leave in leaves if _to_local_date(leave.employee_id, leave.date_to) < today
        ])

    # ------------------------------------------------------------
    # Time rules
    # ------------------------------------------------------------

    def _get_source_extra_fields_domain(self):
        """Only the validated attendances of attendance based employees with a working
        schedule (not flexible) are time rule sources.

        :rtype: list
        """
        return [
            ('state', '=', 'validated'),
            ('employee_id.attendance_based', '=', True),
            ('employee_id.resource_calendar_id.calendar_type', '!=', 'undefined'),
        ]

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

    def _trigger_time_rules_for_affected(self, affected):
        """Only run the rules on create and write for the attendances ending before today: the
        days still running are evaluated by :meth:`_cron_process_day_time_rules`."""
        today = date.today()
        return super()._trigger_time_rules_for_affected(
            [a for a in affected if _to_local_date(a[0], a[2]) < today])

    def _process_time_rules_for(self, affected, rule_period=None, rule_operator=None, rule_week_start=None):
        """Keep the evaluated attendances in the context, see :meth:`_apply_record_output`."""
        return super(HrAttendance, self.with_context(time_rule_collected_ids=set()))._process_time_rules_for(
            affected, rule_period=rule_period, rule_operator=rule_operator, rule_week_start=rule_week_start,
        )

    def _on_sources_collected(self, sources):
        """Reverse the allocation credits of the evaluated attendances, and keep them for
        :meth:`_apply_record_output`.

        :param sources: ``hr.attendance`` records
        """
        self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', sources.ids)
        self.env.context['time_rule_collected_ids'].update(sources.ids)

    def _apply_record_output(self, rules, excess, deficit, active_iv=None):
        """Replace the time rule outputs of the evaluated attendances for ``rules``, see
        ``hr.time.rule._apply_attendance_output``."""
        collected_ids = self.env.context.get('time_rule_collected_ids', set())
        outputs = self.env['hr.leave'].sudo().with_context(**_WORKING_TIME_LEAVE_CTX).search([
            ('attendance_id', 'in', list(collected_ids)),
            ('time_rule_id', 'in', rules.ids),
        ])
        outputs.unlink()
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

    def _get_time_rule_deficit_already_covered(self, rule, start_utc, end_utc):
        """The outputs of the evaluated attendances are deleted before they are applied again.

        :rtype: float
        """
        return 0.0

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

    def _cron_absence_detection(self):
        """Cron: create a validated 1-second technical attendance for each employee without
        attendance yesterday.

        Only for the companies with ``absence_management``, and the employees with a schedule
        whose current version is in contract yesterday. The attendance starts at local midnight
        and has the company's attendance type, so that the daily undertime rules see the day and
        create output time off for the missed hours. Technical attendances without any output
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

        # yesterday is past: creating them runs the daily rules
        technical_attendances = self.env['hr.attendance'].create(technical_attendances_vals)
        to_unlink = technical_attendances.filtered(lambda a: not a.time_rule_leave_ids)
        body = self.env._('This attendance was automatically created to cover an unjustified absence on that day.')
        for technical_attendance in technical_attendances - to_unlink:
            technical_attendance.message_post(body=body)

        to_unlink.unlink()
