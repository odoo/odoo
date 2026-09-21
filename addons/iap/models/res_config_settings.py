from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def iap_action_view_my_services(self):
        return self.env['iap.account'].action_view_my_services()
