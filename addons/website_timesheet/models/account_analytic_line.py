from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _show_portal_timesheets(self):
        """
        Determine if we show timesheet information in the portal.
        """
        domain = [("key", "=", "hr_timesheet.portal_my_home_timesheet")]
        return self.env["ir.ui.view"].sudo().with_context(active_test=False).search(domain).filter_duplicate().active
