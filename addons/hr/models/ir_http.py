from odoo import api, models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @api.model
    def lazy_session_info(self):
        res = super().lazy_session_info()
        res["hrReminder"] = {
            "employee_working_now": self.env.user.employee_id._is_working_now(),
        }
        return res
