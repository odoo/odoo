# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.knowledge.controllers.main import KnowledgeController


class KnowledgeWebsiteController(KnowledgeController):

    # Override routes to display articles to public users
    @http.route('/knowledge/article/<int:article_id>', type='http', auth='public', website=True, sitemap=False)
    def redirect_to_article(self, **kwargs):
        return super().redirect_to_article(**kwargs)

    @http.route('/knowledge/home', type='http', auth='public', website=True, sitemap=False)
    def access_knowledge_home(self):
        return super().access_knowledge_home()

    @http.route('/knowledge/tree_panel/children', type='json', auth='public', website=True, sitemap=False)
    def get_tree_panel_children(self, parent_id):
        return super().get_tree_panel_children(parent_id)
