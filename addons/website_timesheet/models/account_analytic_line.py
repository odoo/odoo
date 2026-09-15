from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.model
    def _show_portal_timesheets(self):
        domain = [("key", "=", "hr_timesheet.portal_my_home_timesheet")]
        _debug.logic("portal_timesheets_visibility_checked")
        return (
            self.env["ir.ui.view"]
            .sudo()
            .with_context(active_test=False)
            .search(domain)
            ._filtered_most_specific()
            .active
        )
