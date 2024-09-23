# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    # Override the method to add 'attendance_ids.work_entry_type_id.is_leave' to the dependencies
    @api.depends('attendance_ids.work_entry_type_id.is_leave')
    def _compute_hours_per_week(self):
        super()._compute_hours_per_week()

    def _get_global_attendances(self):
        return super()._get_global_attendances().filtered(lambda a: not a.work_entry_type_id.is_leave)
