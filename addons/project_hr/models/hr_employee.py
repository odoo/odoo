from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def write(self, vals):
        result = super().write(vals)
        if "resource_id" in vals and self.ids:
            tasks = (
                self.env["project.task"]
                .sudo()
                .search([("employee_ids", "in", self.ids)])
            )
            _debug.pipeline(
                "employee_resource_changed_resyncing_tasks",
                employees=self,
                tasks=tasks,
            )
            if tasks:
                tasks._sync_reservations()
        return result
