# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    # Override the method to add 'attendance_ids.work_entry_type_id' to the dependencies
    @api.depends('attendance_ids.work_entry_type_id')
    def _compute_work_time_rate(self):
        super()._compute_work_time_rate()
