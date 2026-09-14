from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _compute_presence_icon(self):
        super()._compute_presence_icon()
        for employee in self:
            if not employee.is_absent:
                continue
            state = "present" if employee.hr_presence_state == "present" else "absent"
            _debug.logic(
                "presence_icon",
                by="on_leave",
                employee=employee,
                presence=employee.hr_presence_state,
                icon=state,
            )
            employee.hr_icon_display = f"presence_holiday_{state}"
            employee.show_hr_icon_display = True
