# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time, timedelta, UTC
from zoneinfo import ZoneInfo

from odoo import api, models
from odoo.addons.hr_work_entry.models.hr_time_rule import resolve_intervals_by_sequence
from odoo.tools.intervals import Intervals


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def has_static_work_entries(self):
        """Attendance-based versions have no static work entries.

        :rtype: bool
        """
        return not self.attendance_based

    def _get_attendance_intervals(self, start_dt, end_dt):
        """Return empty intervals for the resources of attendance-based versions, the
        schedule intervals for the others.

        :return: ``{resource_id: Intervals}``
        :rtype: dict
        """
        result = {}
        for v in self.filtered('attendance_based'):
            result[v.employee_id.resource_id.id] = Intervals()
        calendar_versions = self.filtered(lambda v: not v.attendance_based)
        if calendar_versions:
            result.update(super(HrVersion, calendar_versions)._get_attendance_intervals(start_dt, end_dt))
        return result

    @api.model
    def _get_work_entry_source_fields(self):
        """Also merge ``attendance_ids`` (and track ``attendance_based``)."""
        return super()._get_work_entry_source_fields() + ['attendance_based', 'attendance_ids']

    def _resolve_attendance_intervals(self, intervals):
        """Split overlapping intervals and pick the winner by time_type.sequence."""
        return resolve_intervals_by_sequence(intervals)

    def _get_version_work_entries_values(self, date_start, date_stop):
        """Add the raw values of the validated, closed attendances of the period.

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
            ('time_type_id.count_as', '=', 'working_time'),
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
                wt_iv_by_rid[rid].append((ci, co, leave.time_type_id))

        for version in self:
            tz = ZoneInfo(version._get_tz())
            rid = version.employee_id.resource_id.id
            default_time_type_id = version._get_default_time_type_id()
            emp_atts = attendances.filtered(lambda a: a.employee_id == version.employee_id)

            raw_att = []
            att_by_range = {}
            for att in emp_atts:
                check_in = att.check_in.replace(tzinfo=UTC)
                check_out = att.check_out.replace(tzinfo=UTC)
                # deficit outputs start after source check_out (unworked time); exclude from time_on
                if not att.source_attendance_id or att.check_in < att.source_attendance_id.check_out:
                    time_on_raw[rid].append((check_in, check_out, dummy))
                if not version.attendance_based:
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
                    time_type = att.time_type_id or self.env['hr.time.type'].browse(default_time_type_id)
                    raw_att.append((check_in, work_check_out, time_type))
                    att_by_range[check_in, work_check_out] = att

            # priority-resolve attendance against wt-leave intervals (lower sequence wins)
            leave_types = {time_type for _, _, time_type in wt_iv_by_rid.get(rid, [])}
            combined = raw_att + wt_iv_by_rid.get(rid, [])
            for seg_start, seg_stop, time_type in self._resolve_attendance_intervals(combined):
                if time_type in leave_types:
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
                    'time_type_id': time_type,
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
        ))._get_version_work_entries_values(date_start, date_stop)

        return base_vals + attendance_vals

    def _get_real_attendances(self, attendances, leaves, worked_leaves):
        """Also remove the days with an attendance (context ``knocked_day_intervals``)."""
        knocked = self.env.context.get('knocked_day_intervals', {}).get(
            self.employee_id.resource_id.id, Intervals()
        )
        return (attendances - knocked) - leaves - worked_leaves

    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        """Values from attendances and from fully flexible versions keep their real duration."""
        if vals.pop('_from_attendance', False):
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

        count_as = self._get_interval_time_type(interval).count_as

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
