from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_asset_log_type(self):
        log_type = super()._get_asset_log_type()
        if not log_type and self.asset_id.kind_code == "vehicle":
            return "service"
        return log_type
