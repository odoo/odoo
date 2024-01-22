from odoo import models


class Http(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        IrConfigSudo = self.env["ir.config_parameter"].sudo()
        session_info = super().session_info()
        session_info.update({"web_m2x_options": IrConfigSudo.get_web_m2x_options()})
        return session_info
