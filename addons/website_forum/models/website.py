# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Website(models.Model):
    _inherit = 'website'

    def _compute_field_forums_count(self):
        Forum = self.env['forum.forum']
        for website in self:
            website.forums_count = Forum.search_count(website.website_domain())

    forums_count = fields.Integer(compute=_compute_field_forums_count)
