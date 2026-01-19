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
