from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

_CONTROLS = ("hr_presence_control_ip", "hr_presence_control_email")


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def set_values(self):
        company = self.company_id
        before = {name: company[name] for name in _CONTROLS}
        super().set_values()
        company.invalidate_recordset(_CONTROLS)
        after = {name: company[name] for name in _CONTROLS}
        if after == before or not any(after.values()):
            return
        _debug.lifecycle(
            "presence_control_changed",
            company=company,
            turned_on=",".join(
                name for name in _CONTROLS if after[name] and not before[name]
            ),
        )
        self.env["hr.employee"]._check_presence()
