# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time, UTC
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.tools.intervals import Intervals


class HrVersion(models.Model):
    _inherit = 'hr.version'

    attendance_based = fields.Boolean(
        string="Attendance Based",
        help="When enabled, payslips are computed from badge records rather than "
             "the employee's work schedule. Time off is always accounted for.",
        groups="hr.group_hr_user",
        default=lambda self: self.env.company.sudo().attendance_based,
    )

    def has_static_work_entries(self):
        return not self.attendance_based

    def _get_attendance_intervals(self, start_dt, end_dt):
        result = {}
        for v in self.filtered('attendance_based'):
            result[v.employee_id.resource_id.id] = Intervals()
        calendar_versions = self.filtered(lambda v: not v.attendance_based)
        if calendar_versions:
            result.update(super(HrVersion, calendar_versions)._get_attendance_intervals(start_dt, end_dt))
        return result

    @api.model
    def _get_work_entry_source_fields(self):
        return super()._get_work_entry_source_fields() + ['attendance_based']

    def _get_version_work_entries_values(self, date_start, date_stop):
        start_dt = date_start.replace(tzinfo=UTC) if not date_start.tzinfo else date_start
        end_dt = date_stop.replace(tzinfo=UTC) if not date_stop.tzinfo else date_stop

        leaves = self.env['hr.leave'].sudo().search([
            '|',
            ('attendance_id', '!=', False),
            ('work_entry_type_id.count_as', '=', 'working_time'),
            ('employee_id', 'in', self.employee_id.ids),
            ('date_from', '<=', end_dt.replace(tzinfo=None)),
            ('date_to', '>=', start_dt.replace(tzinfo=None)),
            ('state', '=', 'validate'),
        ])

        knocked_raw = defaultdict(list)
        time_on_raw = defaultdict(list)
        dummy = self.env['resource.calendar']

        for leave in leaves:
            rid = leave.employee_id.resource_id.id
            tz = ZoneInfo(leave.employee_id.tz or 'UTC')
            if leave.number_of_hours and leave.work_entry_type_id.count_as == 'working_time':
                time_on_raw[rid].append((
                    leave.date_from.replace(tzinfo=UTC),
                    leave.date_to.replace(tzinfo=UTC),
                    leave,
                ))
                if leave.attendance_id:
                    start_day = leave.date_from.replace(tzinfo=UTC).astimezone(tz).date()
                    end_day = leave.date_to.replace(tzinfo=UTC).astimezone(tz).date()
                    knocked_raw[rid].append((
                        datetime.combine(start_day, time.min, tzinfo=tz).astimezone(UTC),
                        datetime.combine(end_day, time.max, tzinfo=tz).astimezone(UTC),
                        dummy,
                    ))

        return super(HrVersion, self.with_context(
            knocked_day_intervals={
                rid: Intervals(items, keep_distinct=True)
                for rid, items in knocked_raw.items()
            },
            time_on_intervals={
                rid: Intervals(items, keep_distinct=True)
                for rid, items in time_on_raw.items()
            },
        ))._get_version_work_entries_values(date_start, date_stop)

    @api.model
    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        res = super()._generate_work_entries_postprocess_adapt_to_calendar(vals)
        if not res:
            return False
        leave_ids = vals.get('leave_ids')
        if leave_ids and leave_ids.attendance_id:
            return False
        return res

    def _get_real_attendances(self, attendances, leaves, worked_leaves):
        knocked = self.env.context.get('knocked_day_intervals', {}).get(
            self.employee_id.resource_id.id, Intervals()
        )
        return (attendances - knocked) - leaves - worked_leaves

    def _get_valid_leave_intervals(self, attendances, interval):
        # worked time wins over absence where they overlap
        payload = interval[2]
        if not payload or payload.work_entry_type.count_as != 'absence':
            return [interval]

        time_on = self.env.context.get('time_on_intervals', {}).get(
            self.employee_id.resource_id.id, Intervals()
        )
        if not time_on:
            return [interval]

        return list(Intervals([interval], keep_distinct=True) - time_on)
