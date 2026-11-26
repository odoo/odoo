# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from odoo import fields, models
from odoo.tools.intervals import Intervals

from odoo.addons.hr_holidays_attendance.models.hr_attendance import _WORKING_TIME_LEAVE_CTX
from odoo.addons.hr_work_entry.models.hr_time_rule import _to_utc


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    # Work of the company's country, else the generic one: the type the rules see attendances as
    condition_work_entry_type_ids = fields.Many2many(
        default=lambda self: self.env.company._get_default_attendance_work_entry_type(),
    )

    def _get_applicable_employees(self, employees):
        """Also drop the employees without schedule for the rules based on the employee
        schedule (``calendar_source = 'employee'``)."""
        result = super()._get_applicable_employees(employees)
        if self.calendar_source == 'employee':
            result = result.filtered('resource_calendar_id')
        return result

    def _apply_attendance_output(self, excess, deficit, active_iv=None):
        """Write the result of :meth:`_evaluate_rules` on attendances as time off, then credit
        or deduct the allocations (:meth:`_apply_allocation_credits`).

        The attendances are left untouched, and the part matching the schedule gives nothing:

        - Excess: each output interval of a rule with a type becomes a time off of that type.
        - Deficit: per period, only the lowest sequence rule is kept; the missing hours are
          placed as time off of the rule's type in the free slots after the deficit start (not
          covered by other attendances), as in :meth:`_apply_output`.

        Allocations are logged on the attendances.

        :param dict excess: ``{employee: {attendance: [_Iv]}}``
        :param dict deficit: ``{employee: {attendance: [(start, stop, rule)]}}``
        :param dict active_iv: unused, the attendances are not split
        :return: the created ``hr.leave``
        """
        create_vals = []
        excess_alloc = []   # [employee, rule, hours, source, log_source]
        deficit_alloc = []  # [employee, rule, hours, source, log_source]
        dummy = self.env['resource.calendar']

        for employee, by_source in deficit.items():
            tz = ZoneInfo(employee._get_tz())
            for attendance, intervals in by_source.items():
                by_period = defaultdict(list)
                for iv_start, iv_end, rule in intervals:
                    if iv_end <= iv_start:
                        continue
                    if rule.quantity_period == 'week':
                        days_to_end = ((int(rule.week_start or '0') - 1) % 7 - iv_start.weekday()) % 7
                        period_key = iv_start.date() + timedelta(days=days_to_end)
                    else:
                        period_key = iv_start.date()
                    by_period[period_key].append((iv_start, iv_end, rule))
                for period_key, period_ivs in by_period.items():
                    winning_rule = min(period_ivs, key=lambda t: t[2].sequence)[2]
                    period_end = _to_utc(datetime.combine(period_key + timedelta(1), time.min), tz)
                    for iv_start, iv_end, rule in period_ivs:
                        if rule != winning_rule:
                            continue
                        hours = (iv_end - iv_start).total_seconds() / 3600
                        deficit_alloc.append([employee, rule, hours, attendance, attendance])
                        if not rule.work_entry_type_id:
                            continue
                        df = _to_utc(iv_start, tz)
                        occupied = attendance._get_time_rule_deficit_occupied(employee.id, df, period_end)
                        remaining = timedelta(hours=hours)
                        for slot_s, slot_e, _dummy in Intervals([(df, period_end, dummy)]) - occupied:
                            if not remaining:
                                break
                            slot_e = min(slot_e, slot_s + remaining)
                            remaining -= slot_e - slot_s
                            create_vals.append(attendance._get_time_rule_output_vals(rule, slot_s, slot_e, rule._get_pp_frozenset()))

        for employee, by_source in excess.items():
            tz = ZoneInfo(employee._get_tz())
            for attendance, intervals in by_source.items():
                # displaced rules still earn the allocation of the hours they claimed
                for iv in intervals:
                    if iv.end > iv.start:
                        for prev_rule in iv.acc:
                            excess_alloc.append([employee, prev_rule, (iv.end - iv.start).total_seconds() / 3600, attendance, attendance])
                for iv in self._resolve_output_intervals(intervals):
                    excess_alloc.append([employee, iv.rule, (iv.end - iv.start).total_seconds() / 3600, attendance, attendance])
                    if iv.rule.work_entry_type_id:
                        create_vals.append(attendance._get_time_rule_output_vals(iv.rule, _to_utc(iv.start, tz), _to_utc(iv.end, tz), iv.pp))

        self._apply_allocation_credits(excess_alloc, deficit_alloc)
        Leave = self.env['hr.leave'].sudo().with_context(**_WORKING_TIME_LEAVE_CTX)
        return Leave.create([vals for vals in create_vals if vals])
