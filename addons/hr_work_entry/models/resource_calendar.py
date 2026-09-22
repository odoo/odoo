from odoo import api, models
from odoo.libs.intervals import Intervals


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    @api.depends("attendance_ids.work_entry_type_id.is_leave")
    def _compute_hours_per_week(self):
        super()._compute_hours_per_week()

    def _get_global_attendances(self):
        return (
            super()
            ._get_global_attendances()
            .filtered(lambda a: not a.work_entry_type_id.is_leave)
        )

    def _work_intervals_batch(
        self,
        start_dt,
        end_dt,
        resources=None,
        domain=None,
        tz=None,
        compute_leaves=True,
    ):
        """Drop the intervals of the schedule lines typed as time off.

        ``_get_global_attendances`` already excludes them, which is what makes
        ``hours_per_week`` read 32 on a calendar whose Friday is typed as
        unpaid. The interval side had never been told, so ``_get_unusual_days``
        went on painting that Friday as a working day and the same calendar
        answered two different things about the same week.

        The lines are filtered out of what ``super()`` returns rather than
        subtracted as a second interval set: a line typed as time off stops
        being work time, it does not carve a hole out of the lines beside it,
        which is the shape ``_get_global_attendances`` already has.
        """
        intervals_per_resource = super()._work_intervals_batch(
            start_dt,
            end_dt,
            resources=resources,
            domain=domain,
            tz=tz,
            compute_leaves=compute_leaves,
        )
        return {
            resource_id: Intervals(
                [
                    interval
                    for interval in intervals
                    # sudo: ``work_entry_type_id`` is behind hr.group_hr_user,
                    # and mrp, project and hr_calendar reach this method as
                    # ordinary users. A flexible resource carries a dummy
                    # attendance with no type at all, hence any() over a
                    # possibly empty mapping rather than a direct read.
                    if not any(interval[2].sudo().mapped("work_entry_type_id.is_leave"))
                ],
                keep_distinct=True,
            )
            for resource_id, intervals in intervals_per_resource.items()
        }
