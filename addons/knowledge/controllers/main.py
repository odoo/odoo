# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import werkzeug
from werkzeug.utils import redirect

from odoo import http
from odoo.http import request


class KnowledgeController(http.Controller):

    # ------------------------
    # Article Access Routes
    # ------------------------

    @http.route('/article/<int:article_id>/invite/<int:partner_id>', type='http', auth='public')
    def article_invite(self, article_id, partner_id, **post):
        article = request.env['knowledge.article'].browse(article_id)
        if not article.exists():
            return werkzeug.exceptions.NotFound()  # (or BadRequest ?)

        partner = article.sudo().article_member_ids.partner_id.filtered(lambda p: p.id == partner_id)
        if not partner:
            raise werkzeug.exceptions.Forbidden()

        if not partner.user_ids:
            partner.signup_get_auth_param()
            signup_url = partner._get_signup_url_for_action(url='/article/%s' % article_id)[partner.id]
            return redirect(signup_url)

        return redirect('/web/login?redirect=/article/%s' % article_id)

    @http.route('/article/<int:article_id>', type='http', auth='user')
    def redirect_to_article(self, article_id, **post):
        article = request.env['knowledge.article'].browse(article_id)
        if not article.exists():
            return werkzeug.exceptions.NotFound()  # (or BadRequest ?)
        # check if user is logged in
        user = request.env.user
        if user._is_public() or not article.sudo().user_has_access:
            raise werkzeug.exceptions.Forbidden()
        if user.has_group('base.group_user'):
            return redirect("/web#id=%s&model=knowledge.article&action=%s&menu_id=%s" % (
                article.id,
                request.env.ref('knowledge.knowledge_article_dashboard_action').id,
                request.env.ref('knowledge.knowledge_menu_root').id
            ))
        return request.render('knowledge.article_frontend_template', self._prepare_article_frontend_values(article, **post))

    def _prepare_article_frontend_values(self, article, **post):
        values = {
            'article': article,
            'article_name': article.name,
            'article_body': article.body,
        }
        values.update(self.get_tree_values())
        return values

    # ------------------------
    # Articles tree generation
    # ------------------------

    def get_tree_values(self):
        # sudo article to avoid access error on member or on article for external users.
        # The article the user can see will be based on user_has_access.
        Article = request.env["knowledge.article"].sudo()
        # get favourite
        favourites = Article.search([("favourite_user_ids", "in", [request.env.user.id]), ('user_has_access', '=', True)])

        main_articles = Article.search([("parent_id", "=", False), ('user_has_access', '=', True)])

        public_articles = main_articles.filtered(lambda article: article.category == 'workspace')
        shared_articles = main_articles.filtered(lambda article: article.category == 'shared')

        values = {
            "favourites": favourites,
            "public_articles": public_articles,
            "shared_articles": shared_articles
        }

        if request.env.user.has_group('base.group_user'):
            values['private_articles'] = main_articles.filtered(lambda article: article.owner_id == request.env.user)
        else:
            values['hide_private'] = True

        return values

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
