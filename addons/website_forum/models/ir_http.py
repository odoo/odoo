from odoo import api, models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        if request.session:
            session_info["public_partner_id"] = request.session.get("partner_id")
        return session_info
