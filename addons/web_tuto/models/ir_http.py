from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        result['tutorial_enabled'] = self.env.user.tutorial_enabled
        result['tutorial_tips_shown'] = self.env.user.tutorial_tips_shown
        result['has_running_tutorials'] = self.env['web_tuto.tutorial'].has_running_tutorials()
        return result
