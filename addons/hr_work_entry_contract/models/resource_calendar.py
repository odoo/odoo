# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import hr_contract


class ResourceCalendar(hr_contract.ResourceCalendar):

    def _get_global_attendances(self):
        return super()._get_global_attendances().filtered(lambda a: not a.work_entry_type_id.is_leave)
