# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _include_all_attendances(self):
        # to override in modules that want to include all work details regardless of
        # `category` in their calculation
        return False

    def _get_working_time_domain(self):
        return Domain.OR([
            Domain('work_entry_type_id', '=', False),
            Domain('work_entry_type_id.category', '=', 'working_time'),
        ])

    # Override the method to add 'attendance_ids.work_entry_type_id.category' to
    # the dependencies
    @api.depends('attendance_ids.work_entry_type_id.category')
    def _compute_hours_per_week(self):
        super()._compute_hours_per_week()

    def _get_global_attendances(self):
        return super()._get_global_attendances().filtered_domain(self._get_working_time_domain())

    def _attendance_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None):
        work_domain = domain if self._include_all_attendances() else Domain.AND([
            domain or Domain.TRUE,
            self._get_working_time_domain(),
        ])
        return super()._attendance_intervals_batch(start_dt, end_dt, resources_per_tz, work_domain)
