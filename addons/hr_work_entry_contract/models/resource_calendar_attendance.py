# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    def _is_work_period(self):
        return super()._is_work_period() and not self.work_entry_type_id.is_leave
