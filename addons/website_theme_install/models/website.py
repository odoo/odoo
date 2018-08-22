# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Website(models.Model):
    _name = "website"
    _inherit = _name

    def button_view_theme(self):
        self._force()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web#action=website_theme_install.theme_install_kanban_action',
            'target': 'self',
        }
