# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    condition_work_entry_type_ids = fields.Many2many(
        default=lambda self: self.env.company.attendance_work_entry_type_id
    )

    can_use_automatic_break = fields.Boolean(
        compute='_compute_can_use_automatic_break', export_string_translation=False,
    )
    automatic_break_duration = fields.Integer(
        string="Automatic Break",
        compute='_compute_automatic_break_duration', store=True, readonly=False,
        help="Break in minutes, deducted once per day when the rule applies. The rules are "
             "checked in sequence, on the worked time minus the breaks of the previous rules "
             "applied, and their breaks add up. It is also added to the automatic check-out time. "
             "0 means no break.",
    )

    @api.depends('threshold_operator', 'quantity_period', 'condition_work_entry_type_ids.count_as')
    def _compute_can_use_automatic_break(self):
        """An automatic break is only allowed on the daily ``exceed`` rules whose time types all
        count as working time."""
        for rule in self:
            rule.can_use_automatic_break = rule._allows_automatic_break()

    def _allows_automatic_break(self):
        """Tell whether the rule can carry an automatic break: a daily ``exceed`` rule whose
        time types all count as working time.

        :rtype: bool
        """
        self.ensure_one()
        types = self.condition_work_entry_type_ids
        return (
            self.threshold_operator == 'exceed'
            and self.quantity_period != 'week'
            and bool(types)
            and all(wet.count_as == 'working_time' for wet in types)
        )

    @api.depends('threshold_operator', 'quantity_period', 'condition_work_entry_type_ids.count_as')
    def _compute_automatic_break_duration(self):
        """Reset the automatic break when the time types do not allow it anymore."""
        for rule in self:
            if not rule._allows_automatic_break():
                rule.automatic_break_duration = 0

    @api.constrains('automatic_break_duration', 'condition_work_entry_type_ids', 'threshold_operator', 'quantity_period')
    def _check_automatic_break(self):
        """Check the automatic break configuration.

        :raise ValidationError: if the break is negative, or set on a rule that is not a daily
            ``exceed`` rule or with a time type that is not working time
        """
        for rule in self.filtered('automatic_break_duration'):
            if rule.automatic_break_duration < 0:
                raise ValidationError(self.env._(
                    "Rule '%(name)s': the automatic break cannot be negative.",
                    name=rule.name,
                ))
            if not rule._allows_automatic_break():
                raise ValidationError(self.env._(
                    "Rule '%(name)s': an automatic break requires a daily rule on excess hours whose time types all count as working time.",
                    name=rule.name,
                ))

    @api.model
    def _get_automatic_break_rules(self, employee, check_in=None, work_entry_type=None):
        """Return the rules giving an automatic break to the employee on the local day of
        ``check_in``: daily ``exceed`` rules with a break whose time types all count as working
        time, applying to the employee, the weekday and ``work_entry_type``.

        :param employee: ``hr.employee``, single record
        :param datetime check_in: naive UTC datetime, now by default
        :param work_entry_type: ``hr.work.entry.type`` of the attendance, the company's
            attendance type by default
        :rtype: ``hr.time.rule``
        """
        employee.ensure_one()
        employee = employee.sudo()
        work_entry_type = work_entry_type or employee.company_id.attendance_work_entry_type_id
        if not work_entry_type:
            return self.browse()
        rules = self.sudo().search([
            ('active', '=', True),
            ('automatic_break_duration', '>', 0),
            ('threshold_operator', '=', 'exceed'),
            ('quantity_period', '!=', 'week'),
            ('condition_work_entry_type_ids', 'in', work_entry_type.ids),
            '|',
                ('company_id', '=', False),
                ('company_id', '=', employee.company_id.id),
        ])
        if not rules:
            return rules
        check_in = check_in or fields.Datetime.now()
        tz = ZoneInfo(employee._get_tz(check_in.date()))
        weekday = check_in.replace(tzinfo=UTC).astimezone(tz).weekday()
        return rules.filtered(lambda rule: (
            rule._allows_automatic_break()
            and rule._weekday_flags()[weekday]
            and rule._get_applicable_employees(employee)
        ))

    @api.model
    def _get_automatic_break_duration(self, employee, net_hours, expected_hours, check_in=None, work_entry_type=None):
        """Return the automatic breaks of a day whose worked time, the breaks deducted, is
        ``net_hours``, as recorded by ``hr.attendance._collect_time_rule_outputs``.

        The rules are taken in sequence: a rule gives its break when the worked time, the breaks
        of the previous rules deducted, exceeds its threshold (expected hours plus employer
        tolerance), else it is skipped. The worked time before the breaks depends on the breaks,
        so the computation is repeated until it is stable. Used to place the automatic check-out.

        :param employee: ``hr.employee``, single record
        :param float net_hours: worked hours of the day, the breaks deducted
        :param float expected_hours: expected hours of the day in the employee's schedule, the
            threshold of the rules based on the schedule
        :param datetime check_in: naive UTC datetime, now by default
        :param work_entry_type: ``hr.work.entry.type`` of the attendance
        :return: hours
        :rtype: float
        """
        rules = self._get_automatic_break_rules(employee, check_in, work_entry_type)
        thresholds = [
            ((expected_hours if rule.calendar_source else rule.expected_hours) + rule.employer_tolerance,
             rule.automatic_break_duration / 60)
            for rule in rules.sorted(lambda r: (r.sequence, r.id))
        ]
        total_break = 0.0
        for _dummy in range(len(thresholds) + 1):
            worked = net_hours + total_break
            new_total = 0.0
            for threshold, break_hours in thresholds:
                if float_compare(worked - new_total, threshold, precision_digits=5) == 1:
                    new_total += break_hours
            if float_compare(new_total, total_break, precision_digits=5) == 0:
                break
            total_break = new_total
        return total_break

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

        ``hr_holidays_attendance`` extends it to credit or deduct allocations. The attendances
        split or reclassified by the rules get a message in their chatter
        (``hr.attendance._log_time_rule_split``).

        :return: the result of ``_apply_output``: ``(new_records, all_source_ids, excess_alloc,
            deficit_alloc)``
        :rtype: tuple
        """
        sources = self.env['hr.attendance'].sudo().union(
            source for by_source in excess.values() for source in by_source
        )
        previous_values = {
            source: (source.work_entry_type_id, source.time_rule_id, source.check_out)
            for source in sources
        }
        result = self._apply_output(excess, deficit, active_iv=active_iv)
        sources._log_time_rule_split(result[0], previous_values)
        return result
