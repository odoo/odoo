# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super().session_info()
        res["can_insert_in_spreadsheet"] = res["can_insert_in_spreadsheet"] or self.env.user.has_group(
            "spreadsheet_dashboard.group_dashboard_manager")
        return res
