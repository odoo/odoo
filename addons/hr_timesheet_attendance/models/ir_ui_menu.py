from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _get_blacklisted_menu_ids(self):
        res = super()._get_blacklisted_menu_ids()
        if not self.env.user.has_group("hr_timesheet.group_hr_timesheet_user") and (
            att_menu := self.env.ref(
                "hr_timesheet_attendance.menu_hr_timesheet_attendance_report",
                raise_if_not_found=False,
            )
        ):
            _debug.logic(
                "attendance_report_menu_hidden", user=self.env.user, menu=att_menu
            )
            res.append(att_menu.id)
        return res
