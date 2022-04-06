# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Article(models.Model):
    _name = 'knowledge.article'
    _inherit = ['knowledge.article', 'website.published.mixin']

    @api.depends('article_url')
    def _compute_website_url(self):
        for record in self:
            record.website_url = record.article_url

    def get_backend_menu_id(self):
        return self.env.ref('knowledge.knowledge_menu_root').id
