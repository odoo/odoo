# coding: utf-8
from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def install_theme_on_current_website(self):
        self.website_id._force()
        action = self.env.ref('website_theme_install.theme_install_kanban_action')
        return action.read()[0]
