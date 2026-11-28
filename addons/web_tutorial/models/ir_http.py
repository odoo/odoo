from odoo import api, models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def lazy_session_info(self):
        result = super().lazy_session_info()
        result['running_tutorials'] = self.env['web_tutorial.tutorial'].get_running_tutorials()
        return result
