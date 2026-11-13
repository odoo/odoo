# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, UTC

from odoo import fields, models
from odoo.fields import Domain
from odoo.tools.intervals import Intervals


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    calendar_type = fields.Selection(
        selection_add=[('attendance', 'Attendances')],
        ondelete={'attendance': 'set default'},
        help="""
    - Fixed: a weekly attendance pattern that repeats identically every week.
    - Variable: attendances set on specific dates rather than a repeating weekly pattern, such as a one-off schedule or a multi-week rotation.
    - Undefined: no predefined slots at all. The resource can work whenever it wants, optionally up to an hours target.
    - Attendances: no predefined slots, the working intervals are the validated attendances of the resource.
        """)

    def _get_attendances_to_unlink(self, next_calendar_type=None):
        """Attendance based calendars have no attendance lines, like undefined ones."""
        to_unlink = super()._get_attendances_to_unlink(next_calendar_type)
        if next_calendar_type == 'attendance':
            return self.attendance_ids
        return to_unlink | self.attendance_ids.filtered(lambda a: a.calendar_id.calendar_type == 'attendance')

    def _attendance_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None):
        """For an attendance based calendar, return the validated ``hr.attendance`` of the
        resources instead of the calendar lines, break excluded.

        The payload of each interval is its ``hr.attendance`` record, so the work entry type
        comes from the attendance. ``domain`` applies to ``hr.attendance``. The ``False`` key
        (no resource) gets no interval.
        """
        if not self or self.calendar_type != 'attendance':
            return super()._attendance_intervals_batch(start_dt, end_dt, resources_per_tz=resources_per_tz, domain=domain)
        assert start_dt.tzinfo and end_dt.tzinfo
        if not resources_per_tz:
            resources_per_tz = {start_dt.tzinfo: self.env['resource.resource']}

        all_resources = self.env['resource.resource'].concat(*resources_per_tz.values())
        attendances = self.env['hr.attendance'].sudo().search(Domain([
            ('employee_id.resource_id', 'in', all_resources.ids),
            ('check_in', '<', end_dt.astimezone(UTC).replace(tzinfo=None)),
            ('check_out', '>', start_dt.astimezone(UTC).replace(tzinfo=None)),
            ('state', '=', 'validated'),
        ]) & Domain(domain or Domain.TRUE))
        attendances_by_resource = attendances.grouped(lambda a: a.employee_id.resource_id)

        result = {False: Intervals()}
        for tz, resources in resources_per_tz.items():
            start = start_dt.astimezone(tz)
            end = end_dt.astimezone(tz)
            for resource in resources:
                intervals = []
                for attendance in attendances_by_resource.get(resource, []):
                    check_in = attendance.check_in.replace(tzinfo=UTC).astimezone(tz)
                    check_out = attendance.check_out.replace(tzinfo=UTC).astimezone(tz)
                    if attendance.break_duration:
                        check_out -= timedelta(hours=attendance.break_duration)
                    check_in, check_out = max(start, check_in), min(end, check_out)
                    if check_in < check_out:
                        intervals.append((check_in, check_out, attendance))
                result[resource.id] = Intervals(intervals, keep_distinct=True)
        return result
