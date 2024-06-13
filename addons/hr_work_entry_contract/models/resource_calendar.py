# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    def _get_global_attendances(self):
        return super()._get_global_attendances().filtered(lambda a: not a.work_entry_type_id.is_leave)
