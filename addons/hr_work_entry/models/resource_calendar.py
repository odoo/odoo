# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    # Override the method to add 'attendance_ids.work_entry_type_id.count_as' to
    # the dependencies
    @api.depends('attendance_ids.work_entry_type_id.count_as')
    def _compute_hours_per_week(self):
        super()._compute_hours_per_week()

    def _get_global_attendances(self):
        global_attendances = super()._get_global_attendances()
        return global_attendances.filtered_domain(
            Domain.OR(
                [
                    Domain('work_entry_type_id', '=', False),
                    Domain('work_entry_type_id.count_as', '=', 'working_time'),
                ],
            ),
        )

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
