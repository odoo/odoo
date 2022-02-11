# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.web.controllers.main import DataSet


class KnowledgeDataSet(DataSet):

    # ------------------------
    # Articles tree generation
    # ------------------------

    def get_tree_values(self):
        Article = request.env["knowledge.article"]
        # get favourite
        favourites = Article.search([("favourite_user_ids", "in", [request.env.user.id])])

        main_articles = Article.search([("parent_id", "=", False)])

        # keep only articles
        public_articles = main_articles.filtered(lambda article: article.category == 'workspace')
        shared_articles = main_articles.filtered(lambda article: article.category == 'shared')
        private_articles = main_articles.filtered(lambda article: article.owner_id == request.env.user)

        return {
            "favourites": favourites,
            "public_articles": public_articles,
            "shared_articles": shared_articles,
            "private_articles": private_articles
        }

    @http.route('/knowledge/get_tree', type='json', auth='user')
    def display_tree(self):
        return request.env.ref('knowledge.knowledge_article_tree_template')._render(self.get_tree_values())

    # ------
    # Others
    # ------

    @http.route('/knowledge/get_articles', type='http', auth="public", methods=['GET'], website=True, sitemap=False)
    def get_articles(self, query='', limit=25, **post):
        Article = request.env['knowledge.article']
        return json.dumps(Article.search_read(
            domain=[('name', '=ilike', '%' + query + '%')],
            fields=['id', 'icon', 'name'],
            limit=int(limit)
        ))
