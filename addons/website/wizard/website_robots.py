# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class WebsiteRobots(models.TransientModel):
    _name = "website.robots"
    _description = "Robots.txt Editor"

    content = fields.Text()

    @api.model
    def default_get(self, fields):
        defaults = super(WebsiteRobots, self).default_get(fields)
        defaults['content'] = self.env['website'].get_current_website().robots_txt
        return defaults

    def action_save(self):
        self.env['website'].get_current_website().robots_txt = self.content
        return {'type': 'ir.actions.act_window_close'}
