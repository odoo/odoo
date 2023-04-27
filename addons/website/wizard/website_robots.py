# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class WebsiteRobots(models.TransientModel):
    _name = "website.robots"
    _description = "Robots.txt Editor"

    content = fields.Text(default=lambda s: s.env['website'].get_current_website().robots_txt)

    def action_save(self):
        self.env['website'].get_current_website().robots_txt = self.content
        return {'type': 'ir.actions.act_window_close'}
