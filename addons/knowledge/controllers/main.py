# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo import http
from odoo.http import request

from odoo.addons.web.controllers.main import DataSet


class KnowledgeDataSet(DataSet):

    @http.route('/knowledge/article/<int:article_id>/rename', type='json', auth="user")
    def article_rename(self, article_id, title):
        request.env['knowledge.article'].browse(article_id).write({'name': title})
        return True

    @http.route('/knowledge/article/<int:article_id>/move', type='json', auth="user")
    def article_move(self, article_id, target_parent_id=False, before_article_id=False):
        Article = request.env['knowledge.article']

        parent = Article.browse(target_parent_id) if target_parent_id else False
        if target_parent_id and not parent:
            return "missing parent"  # The parent in which you want to move your article does not exist anymore
        before_article = Article.browse(before_article_id) if before_article_id else False
        if before_article_id and not before_article:
            return "missing article"  # The article before which you want to move your article does not exist anymore

        article = Article.browse(article_id)
        if before_article:
            article.write({
                'parent_id': target_parent_id,
                'sequence': before_article.sequence
            })
        else:
            # TODO:
            article.write({
                'parent_id': target_parent_id
            })
        return True

    @http.route('/knowledge/article/<int:article_id>/delete', type='json', auth="user")
    def article_delete(self, article_id):
        article = request.env['knowledge.article'].browse(article_id)
        if not article.exists():
            return False
        article.unlink()
        return True

    @http.route('/knowledge/article/<int:article_id>/duplicate', type='json', auth="user")
    def article_duplicate(self, article_id):
        article = request.env['knowledge.article'].browse(article_id)
        if not article.exists():
            return False
        # TODO: Duplicate the article
        return True

    @http.route('/knowledge/article/create', type='json', auth="user")
    def article_create(self, title=False, target_parent_id=False):
        Article = request.env['knowledge.article']
        parent = Article.browse(target_parent_id) if target_parent_id else False
        if target_parent_id and not parent:
            return "missing parent"  # The parent in which you want to create your article does not exist anymore

        values = {'parent_id': target_parent_id}
        if title:
            values.update({'name': title})
        article = Article.create(values)

        return {
            'id': article.id,
            'parent_id': article.parent_id.id,
            'name': article.name,
            'icon': article.icon
        }

    def get_tree_values(self):
        Article = request.env["knowledge.article"]
        # get favourite
        favourites = Article.search([("favourite_user_ids", "in", [request.env.user.id])])

        # get public articles
        public_articles = Article.search([("owner_id", "=", False), ("parent_id", "=", False)])

        # get private articles
        private_articles = Article.search([("owner_id", "=", request.env.user.id), ("parent_id", "=", False)])

        return {
            "favourites": favourites,
            "public_articles": public_articles,
            "private_articles": private_articles
        }

    @http.route('/knowledge/get_tree_html', type="json", auth="user")
    def get_tree_html(self):
        return {
            'tree_html': request.env.ref('knowledge.knowledge_article_tree_template')._render(self.get_tree_html)
        }

    @http.route('/knowledge/get_tree', type='json', auth='user')
    def display_tree(self):
        return request.env.ref('knowledge.knowledge_article_tree_template')._render(self.get_tree_values())

    @http.route('/knowledge/get_articles', type='http', auth="public", methods=['GET'], website=True, sitemap=False)
    def get_articles(self, query='', limit=25, **post):
        Article = request.env['knowledge.article']
        return json.dumps(Article.search_read(
            domain=[('name', '=ilike', '%' + query + '%')],
            fields=['id', 'name'],
            limit=int(limit)
        ))