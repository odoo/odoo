# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time, timedelta, UTC
from itertools import pairwise
from zoneinfo import ZoneInfo

from odoo import api, models
from odoo.addons.hr_work_entry.models.hr_time_rule import resolve_intervals_by_sequence
from odoo.tools.intervals import Intervals


class HrVersion(models.Model):
    _inherit = 'hr.version'

    @api.model
    def _get_work_entry_source_fields(self):
        """Also merge ``attendance_ids``."""
        return super()._get_work_entry_source_fields() + ['attendance_ids']

    def _resolve_attendance_intervals(self, intervals):
        """Split overlapping intervals and pick the winner by work_entry_type.sequence."""
        return resolve_intervals_by_sequence(intervals)

    def _get_version_work_entries_values(self, date_start, date_stop):
        """Add the raw values of the validated, closed attendances of the period, except for the
        attendance based versions.

        Each attendance gives a value of its own type, from ``check_in`` to ``check_out`` minus
        the break, with the key ``attendance_ids``; where an attendance and a working time
        leave overlap, the lowest type sequence wins. The schedule part is computed by
        ``super()`` with three context keys (``{resource_id: Intervals}``, aware UTC):

        - ``knocked_day_intervals``: for static versions, the local days with an attendance,
          removed from the schedule (:meth:`_get_real_attendances`);
        - ``time_on_intervals``: the worked time (attendances and working time leaves), cut out
          of the absences (:meth:`_get_valid_leave_intervals`);
        - ``att_coverage_intervals``: the attendance segments that won over a working time
          leave, cut out of that leave.

        :param datetime date_start: naive or aware (UTC)
        :param datetime date_stop: naive or aware (UTC)
        :rtype: list[dict]
        """
        start_dt = date_start.replace(tzinfo=UTC) if not date_start.tzinfo else date_start
        end_dt = date_stop.replace(tzinfo=UTC) if not date_stop.tzinfo else date_stop

        # working-time leaves from the leave pipeline
        working_time_leaves = self.env['hr.leave'].sudo().search([
            ('work_entry_type_id.count_as', '=', 'working_time'),
            ('employee_id', 'in', self.employee_id.ids),
            ('date_from', '<=', end_dt.replace(tzinfo=None)),
            ('date_to', '>=', start_dt.replace(tzinfo=None)),
            ('state', '=', 'validate'),
        ])

        attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', 'in', self.employee_id.ids),
            ('check_in', '<=', end_dt.replace(tzinfo=None)),
            ('check_out', '>=', start_dt.replace(tzinfo=None)),
            ('check_out', '!=', False),
            ('state', '=', 'validated'),
        ])

        knocked_raw = defaultdict(list)
        time_on_raw = defaultdict(list)
        att_coverage_raw = defaultdict(list)
        dummy = self.env['resource.calendar']
        attendance_vals = []

        wt_iv_by_rid = defaultdict(list)
        for leave in working_time_leaves:
            rid = leave.employee_id.resource_id.id
            if leave.number_of_hours:
                ci = leave.date_from.replace(tzinfo=UTC)
                co = leave.date_to.replace(tzinfo=UTC)
                time_on_raw[rid].append((ci, co, dummy))
                wt_iv_by_rid[rid].append((ci, co, leave.work_entry_type_id))

        # attendance based with a schedule: the worked hours of each local day, see _get_real_attendances
        worked_hours_raw = defaultdict(lambda: defaultdict(float))
        based_employees = self.filtered(lambda v: v.work_entry_source == 'attendance' and not v._is_flexible()).employee_id
        for att in attendances.filtered(lambda a: a.employee_id in based_employees):
            tz = ZoneInfo(att.employee_id._get_tz())
            rid = att.employee_id.resource_id.id
            start, stop = (moment.replace(tzinfo=UTC).astimezone(tz) for moment in (att.check_in, att.check_out))
            worked_hours_raw[rid][start.date()] -= att.break_duration
            while start < stop:
                day_stop = min(stop, datetime.combine(start.date() + timedelta(days=1), time.min, tzinfo=tz))
                worked_hours_raw[rid][start.date()] += (day_stop - start).total_seconds() / 3600
                start = day_stop

        for version in self:
            # attendance based: the schedule and the time off of the attendances give the entries
            if not version.has_static_work_entries() or version._is_flexible() or version.work_entry_source == 'attendance':
                continue
            tz = ZoneInfo(version._get_tz())
            rid = version.employee_id.resource_id.id
            default_wet_id = version._get_default_work_entry_type_id()
            emp_atts = attendances.filtered(lambda a: a.employee_id == version.employee_id)

            raw_att = []
            att_by_range = {}
            for att in emp_atts:
                check_in = att.check_in.replace(tzinfo=UTC)
                check_out = att.check_out.replace(tzinfo=UTC)
                time_on_raw[rid].append((check_in, check_out, dummy))
                start_day = check_in.astimezone(tz).date()
                end_day = check_out.astimezone(tz).date()
                knocked_raw[rid].append((
                    datetime.combine(start_day, time.min, tzinfo=tz).astimezone(UTC),
                    datetime.combine(end_day, time.max, tzinfo=tz).astimezone(UTC),
                    dummy,
                ))
                # exclude break from worked time
                work_check_out = check_out - timedelta(hours=att.break_duration) if att.break_duration else check_out
                if work_check_out > check_in:
                    wet = self.env['hr.work.entry.type'].browse(default_wet_id)
                    raw_att.append((check_in, work_check_out, wet))
                    att_by_range[check_in, work_check_out] = att

            # priority-resolve attendance against wt-leave intervals (lower sequence wins)
            combined = raw_att + wt_iv_by_rid.get(rid, [])
            for seg_start, seg_stop, wet in self._resolve_attendance_intervals(combined):
                if any(
                    leave_start <= seg_start and seg_stop <= leave_stop and leave_wet == wet
                    for leave_start, leave_stop, leave_wet in wt_iv_by_rid.get(rid, [])
                ):
                    # wt-leave won; so we skip and let base handle it
                    continue
                # attendance won: look up the source record (dict miss on split sub-segments,
                # fall back to the original attendance that contains this segment)
                att = att_by_range.get((seg_start, seg_stop)) or next(
                    (att_by_range[ci, co] for ci, co, _ in raw_att if ci <= seg_start and co >= seg_stop),
                    None,
                )
                att_coverage_raw[rid].append((seg_start, seg_stop, dummy))
                extra = version._get_more_vals_attendance_interval((seg_start, seg_stop, att)) if att else []
                attendance_vals.append({
                    'date_start': seg_start.replace(tzinfo=None),
                    'date_stop': seg_stop.replace(tzinfo=None),
                    'work_entry_type_id': wet,
                    'employee_id': version.employee_id,
                    'version_id': version,
                    'company_id': version.company_id,
                    '_from_attendance': True,
                    **dict(extra),
                })

        base_vals = super(HrVersion, self.with_context(
            knocked_day_intervals={
                rid: Intervals(items, keep_distinct=True)
                for rid, items in knocked_raw.items()
            },
            time_on_intervals={
                rid: Intervals(items, keep_distinct=True)
                for rid, items in time_on_raw.items()
            },
            att_coverage_intervals={
                rid: Intervals(items, keep_distinct=True)
                for rid, items in att_coverage_raw.items()
            },
            attendance_worked_hours={
                employee.resource_id.id: worked_hours_raw[employee.resource_id.id] for employee in based_employees
            },
        ))._get_version_work_entries_values(date_start, date_stop)

        return base_vals + attendance_vals

    def _get_real_attendances(self, attendances, leaves, worked_leaves):
        """Also remove the days with an attendance (context ``knocked_day_intervals``).

        For the attendance based versions with a schedule (context ``attendance_worked_hours``,
        the worked hours of each local day), the time rule outputs of the attendances count by
        duration, not by time: on top of the schedule for the hours worked beyond it, else in
        place of scheduled hours, removed from the end of the day."""
        rid = self.employee_id.resource_id.id
        knocked = self.env.context.get('knocked_day_intervals', {}).get(rid, Intervals())
        worked_hours = self.env.context.get('attendance_worked_hours', {}).get(rid)
        if worked_hours is None:
            return (attendances - knocked) - leaves - worked_leaves
        outputs, others = [], []
        for part in self._split_worked_leaves(worked_leaves):
            (outputs if part[2].holiday_id.time_rule_id and part[2].holiday_id.attendance_id else others).append(part)
        output_hours = defaultdict(float)
        for start, stop, _leave in outputs:
            output_hours[start.date()] += (stop - start).total_seconds() / 3600
        schedule_by_day = defaultdict(list)
        for interval in (attendances - knocked) - leaves - Intervals(others, keep_distinct=True):
            schedule_by_day[interval[0].date()].append(interval)
        result = []
        for day, intervals in schedule_by_day.items():
            scheduled = sum((stop - start).total_seconds() / 3600 for start, stop, _payload in intervals)
            to_remove = max(0.0, output_hours[day] - max(0.0, worked_hours.get(day, 0.0) - scheduled))
            for start, stop, payload in reversed(intervals):
                hours = (stop - start).total_seconds() / 3600
                if to_remove >= hours:
                    to_remove -= hours
                    continue
                result.append((start, stop - timedelta(hours=to_remove), payload))
                to_remove = 0.0
        return Intervals(result, keep_distinct=True)

    def _split_worked_leaves(self, worked_leaves):
        """Return the worked leaves with one leave per interval, clipped to its own span: the
        intervals merge the overlapping leaves.

        :rtype: list
        """
        return [
            (
                max(start, leave.date_from.replace(tzinfo=UTC).astimezone(start.tzinfo)),
                min(stop, leave.date_to.replace(tzinfo=UTC).astimezone(start.tzinfo)),
                leave,
            )
            for start, stop, calendar_leaves in worked_leaves
            for leave in calendar_leaves
        ]

    def _get_real_worked_leaves(self, worked_leaves, real_leaves):
        """Where worked leaves overlap (e.g. the time off of an attendance and a time off
        request), the type with the lowest sequence wins: each leave only keeps its own span."""
        worked_leaves = super()._get_real_worked_leaves(worked_leaves, real_leaves)
        if all(len(calendar_leaves) <= 1 for _start, _stop, calendar_leaves in worked_leaves):
            return worked_leaves
        parts = self._split_worked_leaves(worked_leaves)
        times = sorted({moment for start, stop, _leave in parts for moment in (start, stop)})
        resolved = []
        for slice_start, slice_stop in pairwise(times):
            covering = [leave for start, stop, leave in parts if start <= slice_start and slice_stop <= stop]
            if covering:
                resolved.append((slice_start, slice_stop, min(
                    covering, key=lambda leave: self._get_interval_work_entry_type((slice_start, slice_stop, leave)).sequence)))
        return Intervals(resolved, keep_distinct=True)

    def _get_interval_own_leaves(self, interval, leaves):
        """Return the leaves to consider for ``interval``: only its own leave when several worked
        leaves cover it, merged in one interval of ``leaves`` or not, resolved by
        :meth:`_get_real_worked_leaves`. An interval of the schedule (the absences) has no leave
        of its own.

        :rtype: list
        """
        if interval[2] and interval[2]._name == 'resource.calendar.leaves' and len(interval[2]) == 1 and sum(
            len(leave[2]) for leave in leaves if leave[2] and leave[0] <= interval[0] and interval[1] <= leave[1]
        ) > 1:
            return [interval]
        return leaves

    def _get_more_vals_leave_interval(self, interval, leaves):
        """Only the own leave of an interval of overlapping worked leaves, see
        :meth:`_get_interval_own_leaves`."""
        return super()._get_more_vals_leave_interval(interval, self._get_interval_own_leaves(interval, leaves))

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        """Only the own leave of an interval of overlapping worked leaves, see
        :meth:`_get_interval_own_leaves`."""
        return super()._get_interval_leave_work_entry_type(interval, self._get_interval_own_leaves(interval, leaves), bypassing_codes)

    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        """Values from attendances, from their working time leaves and from fully flexible
        versions keep their real duration."""
        if vals.pop('_from_attendance', False):
            return False
        if vals.get('leave_ids') and vals['leave_ids'].attendance_id:
            return False
        # fully-flexible employees have no calendar; compute duration from actual time span
        version = vals.get('version_id')
        if version and version._is_fully_flexible():
            return False
        return super()._generate_work_entries_postprocess_adapt_to_calendar(vals)

    def _get_more_vals_attendance_interval(self, interval):
        """Add ``('attendance_ids', attendance)`` when the payload is an ``hr.attendance``."""
        vals = super()._get_more_vals_attendance_interval(interval)
        att = interval[2]
        if att and hasattr(att, '_name') and att._name == 'hr.attendance':
            vals.append(('attendance_ids', att))
        return vals

    def _get_valid_leave_intervals(self, attendances, interval):
        """Cut absences where the employee worked (context ``time_on_intervals``) and working
        time leaves where an attendance won (context ``att_coverage_intervals``).

        :rtype: list
        """
        payload = interval[2]
        if not payload:
            return [interval]

        if not super()._get_valid_leave_intervals(attendances, interval):
            return []

        count_as = self._get_interval_work_entry_type(interval).count_as

        if count_as == 'absence':
            # worked time wins over absence where they overlap
            time_on = self.env.context.get('time_on_intervals', {}).get(
                self.employee_id.resource_id.id, Intervals()
            )
            if not time_on:
                return [interval]
            return list(Intervals([interval], keep_distinct=True) - time_on)

        if count_as == 'working_time':
            # suppress base's wt-leave output for portions where attendance won the fight
            att_coverage = self.env.context.get('att_coverage_intervals', {}).get(
                self.employee_id.resource_id.id, Intervals()
            )
            if not att_coverage:
                return [interval]
            return list(Intervals([interval], keep_distinct=True) - att_coverage)

        return [interval]
