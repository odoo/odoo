# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    # Override the method to add 'attendance_ids.work_entry_type_id.count_as' to
    # the dependencies
    @api.depends('attendance_ids.work_entry_type_id.count_as')
    def _compute_hours_per_week(self):
        super()._compute_hours_per_week()

    @api.depends('attendance_ids.work_entry_type_id.count_as')
    def _compute_days_per_week(self):
        super()._compute_days_per_week()

    @api.depends('attendance_ids.work_entry_type_id.count_as')
    def _compute_hours_per_day(self):
        super()._compute_hours_per_day()

    def _get_reference_hours_per_day(self, day):
        """
        Attendances counted as an absence, like a partial incapacity or a rest day, are left out
        of hours_per_day, but the employee is not available on them either. The theoretical day
        of such a day is therefore the whole span the calendar defines for it.
        """
        hours_per_day = super()._get_reference_hours_per_day(day)
        attendances = self.sudo().attendance_ids._filter_by_date(day)
        has_absence = any(attendance.work_entry_type_id.count_as == 'absence' for attendance in attendances)
        # Only a day holding an absence needs another reference than the average day.
        if not has_absence:
            return hours_per_day
        # The average day stays a minimum, so a day made of absences only still counts in full.
        return max(hours_per_day, sum(attendances.mapped('duration_hours')))

    def _work_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None, compute_leaves=True):
        work_intervals = super()._work_intervals_batch(
            start_dt,
            end_dt,
            resources_per_tz=resources_per_tz,
            domain=domain,
            compute_leaves=compute_leaves,
        )

        if not compute_leaves:
            return work_intervals

        all_resources = set()
        if not resources_per_tz or self:
            all_resources.add(self.env["resource.resource"])
        if resources_per_tz:
            for _, resources in resources_per_tz.items():
                all_resources |= set(resources)

        leave_attendance_intervals = self.sudo()._attendance_intervals_batch(
            start_dt,
            end_dt,
            resources_per_tz=resources_per_tz,
            domain=[("work_entry_type_id.count_as", "=", "absence")],
        )
        return {r.id: (work_intervals[r.id] - leave_attendance_intervals[r.id]) for r in all_resources}
