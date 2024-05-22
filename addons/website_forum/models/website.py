# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.addons.http_routing.models.ir_http import url_for


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def get_default_forum_count(self):
        self.forums_count = self.env['forum.forum'].search_count(self.website_domain())

    forums_count = fields.Integer(readonly=True, default=get_default_forum_count)

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Forum'), url_for('/forum'), 'website_forum'))
        return suggested_controllers
