# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrEmployee(models.AbstractModel):
    _inherit = "hr.employee"

    def _get_tz(self):
        return self.sudo().contract_id.resource_calendar_id.tz or super()._get_tz()
