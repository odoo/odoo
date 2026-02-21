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

    def _get_working_attendances(self):
        global_attendances = super()._get_working_attendances()
        return global_attendances.filtered(lambda att: (not att.sudo().work_entry_type_id) or att.sudo().work_entry_type_id.count_as == 'working_time')
