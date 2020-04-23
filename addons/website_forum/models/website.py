# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.addons.http_routing.models.ir_http import url_for


class Website(models.Model):
    _inherit = 'website'

    def _compute_field_forums_count(self):
        Forum = self.env['forum.forum']
        for website in self:
            website.forums_count = Forum.search_count(website.website_domain())

    forums_count = fields.Integer(compute=_compute_field_forums_count)

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Forum'), url_for('/forum'), 'website_forum'))
        return suggested_controllers
