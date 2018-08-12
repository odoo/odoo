# coding: utf-8
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def website_install_theme(self):
        self.website_id._fix_to_session()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web#action=website_theme_install.theme_install_kanban_action',
            'target': 'self',
        }
