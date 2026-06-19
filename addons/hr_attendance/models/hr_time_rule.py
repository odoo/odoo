# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC
from zoneinfo import ZoneInfo

from odoo import fields, models
from odoo.addons.hr_work_entry.models.hr_time_rule import resolve_intervals_by_sequence
from odoo.tools.intervals import Intervals


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    condition_work_entry_type_ids = fields.Many2many(
        default=lambda self: self.env.ref('hr_work_entry.attendance_work_entry_type', raise_if_not_found=False),
    )

    def _get_applicable_employees(self, employees):
        result = super()._get_applicable_employees(employees)
        if self.calendar_source == 'employee':
            result = result.filtered('resource_calendar_id')
        return result

    def _get_remainder_attendance_vals(self, employee, source_attendance, check_in, check_out):
        return {
            'employee_id': employee.id,
            'work_entry_type_id': source_attendance.work_entry_type_id.id,
            'check_in': check_in,
            'check_out': check_out,
            'source_attendance_id': source_attendance.id,
        }

    def _get_output_attendance_vals(self, employee, rule, check_in, check_out, source_attendance=None):
        return {
            'employee_id': employee.id,
            'work_entry_type_id': rule.work_entry_type_id.id,
            'check_in': check_in,
            'check_out': check_out,
            'is_time_rule_output': True,
            'source_attendance_id': source_attendance.id if source_attendance else False,
            'time_rule_id': rule.id,
        }

    def _resolve_output_intervals(self, intervals):
        """For each time slice, the lowest-sequence rule with a work entry type wins."""
        valid = [(s, e, rule) for s, e, rule in intervals if rule.work_entry_type_id]
        return resolve_intervals_by_sequence(valid)

    def _apply_attendance_output(self, excess, deficit):
        """Create output and remainder attendance records from the computed excess/deficit."""
        Attendance = self.env['hr.attendance'].sudo()
        auto_ctx = dict(skip_time_rules=True, tracking_disable=True)
        att_create_vals = []
        archive_source_ids = []
        dummy = self.env['resource.calendar']

        for employee, by_source in excess.items():
            tz = ZoneInfo(employee._get_tz())
            for source_att, intervals in by_source.items():
                # day-rule intervals: archive source + create remainder + create outputs
                day_ivs = [(s, e, r) for s, e, r in intervals if r.quantity_period != 'week']
                day_output_intervals = self._resolve_output_intervals(day_ivs)
                if day_output_intervals:
                    archive_source_ids.append(source_att.id)
                    src_start = source_att.check_in.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
                    src_stop = source_att.check_out.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
                    out_union = Intervals([(s, e, dummy) for s, e, _ in day_output_intervals], keep_distinct=True)
                    for s, e, _ in Intervals([(src_start, src_stop, dummy)]) - out_union:
                        att_create_vals.append(self._get_remainder_attendance_vals(
                            employee, source_att,
                            s.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None),
                            e.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None),
                        ))
                    for s, e, rule in day_output_intervals:
                        ci = s.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                        co = e.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                        att_create_vals.append(self._get_output_attendance_vals(employee, rule, ci, co, source_att))

                # week-rule intervals: source stays active, just emit the output record
                week_ivs = [(s, e, r) for s, e, r in intervals if r.quantity_period == 'week']
                for s, e, rule in self._resolve_output_intervals(week_ivs):
                    ci = s.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    co = e.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    att_create_vals.append(self._get_output_attendance_vals(employee, rule, ci, co, source_att))

        for employee, by_source in deficit.items():
            tz = ZoneInfo(employee._get_tz())
            for source_att, intervals in by_source.items():
                effective_rule = min(
                    (rule for _, _, rule in intervals if rule.work_entry_type_id),
                    key=lambda r: r.sequence,
                    default=None,
                )
                if not effective_rule:
                    continue
                for s, e, rule in intervals:
                    if rule != effective_rule or e <= s:
                        continue
                    ci = s.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    co = e.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    att_create_vals.append(self._get_output_attendance_vals(employee, rule, ci, co, source_att))

        if archive_source_ids:
            Attendance.browse(archive_source_ids).with_context(**auto_ctx).write({'active': False})

        Attendance.with_context(**auto_ctx).create(att_create_vals)
