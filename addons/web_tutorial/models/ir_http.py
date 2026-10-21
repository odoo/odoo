from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        result['running_tutorials'] = self.env['web_tutorial.tutorial'].get_running_tutorials()
        return result
