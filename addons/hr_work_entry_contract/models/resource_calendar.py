# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons.hr_work_entry_contract.models.hr_work_intervals import WorkIntervals


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    # Override the method to add 'attendance_ids.work_entry_type_id.is_leave' to the dependencies
    @api.depends('attendance_ids.work_entry_type_id.is_leave')
    def _compute_hours_per_week(self):
        super()._compute_hours_per_week()

    def _get_global_attendances(self):
        return super()._get_global_attendances().filtered(lambda a: not a.work_entry_type_id.is_leave)

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, lunch=False):
        result_per_resource_id = super()._attendance_intervals_batch(start_dt, end_dt, resources, domain, tz, lunch)
        if self.env.context.get('with_is_leave'):
            return result_per_resource_id
        res_without_is_leave = dict()
        for res_id, attendance_intervals in result_per_resource_id.items():
            res_without_is_leave[res_id] = WorkIntervals(
                [(start, stop, attendance) for (start, stop, attendance) in attendance_intervals
                    if not attendance.sudo().work_entry_type_id or
                        (attendance.sudo().work_entry_type_id and not attendance.sudo().work_entry_type_id.is_leave)
                ]
            )
        return res_without_is_leave
