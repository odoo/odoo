# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.model
    def _format_portal_hours(self, hours):
        sign = "-" if hours < 0 else ""
        display_hours, minutes = divmod(round(abs(hours) * 60), 60)
        kwargs = {"sign": sign, "hours": display_hours, "minutes": minutes}
        if display_hours and minutes:
            return self.env._("%(sign)s%(hours)sh %(minutes)sm", **kwargs)
        if display_hours:
            return self.env._("%(sign)s%(hours)sh", **kwargs)
        return self.env._("%(sign)s%(minutes)sm", **kwargs)
