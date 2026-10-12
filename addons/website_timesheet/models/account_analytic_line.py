from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _show_portal_timesheets(self):
        """
        Determine if we show timesheet information in the portal.
        """
        entry = self.env.ref("hr_timesheet.portal_timesheets", raise_if_not_found=False)
        return bool(entry and entry.show_in_portal)
