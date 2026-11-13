# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from odoo.tools.date_utils import sum_intervals


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    condition_work_entry_type_ids = fields.Many2many(
        default=lambda self: self.env.company.attendance_work_entry_type_id
    )

    can_use_automatic_break = fields.Boolean(
        compute='_compute_can_use_automatic_break', export_string_translation=False,
    )
    automatic_break = fields.Boolean(
        string="Automatic Break", default=False,
        compute='_compute_automatic_break', store=True, readonly=False,
        help="Deduct a break from the attendances of the employees whose scheduled work time of "
             "the day is within the given range. The break is also added to the automatic "
             "check-out time.",
    )
    break_min_work_hours = fields.Float(string="Minimum Work Time", default=0.0)
    break_max_work_hours = fields.Float(string="Maximum Work Time", default=24.0)
    automatic_break_duration = fields.Float(string="Break Duration")

    @api.depends('condition_work_entry_type_ids.count_as')
    def _compute_can_use_automatic_break(self):
        """An automatic break is only allowed when all the time types of the rule count as
        working time."""
        for rule in self:
            types = rule.condition_work_entry_type_ids
            rule.can_use_automatic_break = bool(types) and all(
                wet.count_as == 'working_time' for wet in types
            )

    @api.depends('condition_work_entry_type_ids.count_as')
    def _compute_automatic_break(self):
        """Reset ``automatic_break`` when the time types do not allow it anymore."""
        for rule in self:
            if not rule.can_use_automatic_break:
                rule.automatic_break = False

    @api.constrains(
        'automatic_break', 'break_min_work_hours', 'break_max_work_hours',
        'automatic_break_duration', 'condition_work_entry_type_ids',
    )
    def _check_automatic_break(self):
        """Check the automatic break configuration.

        :raise ValidationError: if a time type is not working time, if the work time range is
            invalid or if the break duration is not positive
        """
        for rule in self.filtered('automatic_break'):
            if not rule.can_use_automatic_break:
                raise ValidationError(self.env._(
                    "Rule '%(name)s': an automatic break requires all its time types to count as working time.",
                    name=rule.name,
                ))
            if not (0 <= rule.break_min_work_hours <= rule.break_max_work_hours <= 24):
                raise ValidationError(self.env._(
                    "Rule '%(name)s': the work time range of the automatic break must be between 0 and 24 hours, "
                    "with the minimum lower than the maximum.",
                    name=rule.name,
                ))
            if float_compare(rule.automatic_break_duration, 0.0, precision_digits=4) <= 0:
                raise ValidationError(self.env._(
                    "Rule '%(name)s': the automatic break duration must be positive.",
                    name=rule.name,
                ))

    @api.model
    def _get_automatic_break_duration(self, employee, check_in=None):
        """Return the automatic break of the employee for the local day of ``check_in``.

        The scheduled slots of the day (``hr.employee._get_expected_attendances``) are matched
        against the active rules with ``automatic_break``: a rule applies when it applies to the
        employee and to the weekday, and when the scheduled hours of its time types (a slot
        without time type counts as the company's attendance type) are within
        ``[break_min_work_hours, break_max_work_hours[``. The first rule (``sequence, id``) wins.

        :param employee: ``hr.employee``, single record
        :param datetime check_in: naive UTC datetime, now by default
        :return: hours, ``0.0`` without matching rule
        :rtype: float
        """
        employee.ensure_one()
        employee = employee.sudo()
        rules = self.sudo().search([
            ('active', '=', True),
            ('automatic_break', '=', True),
            '|',
                ('company_id', '=', False),
                ('company_id', '=', employee.company_id.id),
        ])
        if not rules:
            return 0.0

        check_in = check_in or fields.Datetime.now()
        tz = ZoneInfo(employee._get_tz(check_in.date()))
        local_check_in = check_in.replace(tzinfo=UTC).astimezone(tz)
        day_start = local_check_in.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        weekday = day_start.weekday()

        rules = rules.filtered(lambda r: r._weekday_flags()[weekday] and r._get_applicable_employees(employee))
        if not rules:
            return 0.0

        if not employee.resource_calendar_id:
            return 0.0
        default_type = employee.company_id.attendance_work_entry_type_id
        slots = [
            (start, stop, self._get_slot_work_entry_types(slot, default_type))
            for start, stop, slot in employee._get_expected_attendances(day_start, day_end)
        ]
        for rule in rules:  # already ordered by sequence, id
            rule_types = rule.condition_work_entry_type_ids
            matching = [(start, stop, types) for start, stop, types in slots if types & rule_types]
            if not matching:
                continue
            scheduled_hours = sum_intervals(matching)
            if (
                float_compare(scheduled_hours, rule.break_min_work_hours, precision_digits=4) >= 0
                and float_compare(scheduled_hours, rule.break_max_work_hours, precision_digits=4) < 0
            ):
                return rule.automatic_break_duration
        return 0.0

    def _get_applicable_employees(self, employees):
        """Also drop the employees without schedule for the rules based on the employee
        schedule (``calendar_source = 'employee'``)."""
        result = super()._get_applicable_employees(employees)
        if self.calendar_source == 'employee':
            result = result.filtered('resource_calendar_id')
        return result

    def _get_output_attendance_vals(self, employee, check_in, check_out, source_attendance=None, accumulated_pp=frozenset()):
        """Return the creation values of an output attendance of the rule.

        :param employee: ``hr.employee``
        :param datetime check_in: naive UTC
        :param datetime check_out: naive UTC
        :param source_attendance: the source ``hr.attendance``
        :param frozenset accumulated_pp: premium pay ids, used by overrides (``hr_payroll``)
        :return: ``employee_id``, ``work_entry_type_id`` (the rule's output type),
            ``check_in``, ``check_out``, ``source_attendance_id`` and ``time_rule_id``
        :rtype: dict
        """
        self.ensure_one()
        return {
            'employee_id': employee.id,
            'work_entry_type_id': self.work_entry_type_id.id,
            'check_in': check_in,
            'check_out': check_out,
            'source_attendance_id': source_attendance.id if source_attendance else False,
            'time_rule_id': self.id,
        }

    def _apply_attendance_output(self, excess, deficit, active_iv=None):
        """Write the time rule results on attendances (``hr.time.rule._apply_output``).

        ``hr_holidays_attendance`` extends it to credit or deduct allocations.

        :return: the result of ``_apply_output``: ``(new_records, all_source_ids, excess_alloc,
            deficit_alloc)``
        :rtype: tuple
        """
        return self._apply_output(excess, deficit, active_iv=active_iv)

    @api.model
    def _get_slot_work_entry_types(self, slot, default_type):
        """Return the time types of an expected attendance slot.

        :param slot: ``resource.calendar.attendance``, payload of an interval of
            ``hr.employee._get_expected_attendances`` (several records when merged)
        :param default_type: ``hr.work.entry.type`` used for the slots without time type
        :rtype: hr.work.entry.type
        """
        slot = slot.sudo()
        types = slot.work_entry_type_id
        if not slot or any(not s.work_entry_type_id for s in slot):
            types |= default_type
        return types
