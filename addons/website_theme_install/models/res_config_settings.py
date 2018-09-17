# coding: utf-8
from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def install_theme_on_current_website(self):
        self.website_id._force()
        action = self.env.ref('website_theme_install.theme_install_kanban_action')
        return action.read()[0]

    def action_website_create_new(self):
        res = super(ResConfigSettings, self).action_website_create_new()
        res['view_id'] = self.env.ref('website_theme_install.view_website_form_view_themes_modal').id
        return res
