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

        partner = article.main_article_id.sudo().article_member_ids.partner_id.filtered(lambda p: p.id == partner_id)
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
        # for external_users, need to sudo to access article.user_has_access and other fields needed to render the page.
        article = article.sudo()
        if user._is_public() or not article.user_has_access:
            raise werkzeug.exceptions.Forbidden()
        if user.has_group('base.group_user'):
            return redirect("/web#id=%s&model=knowledge.article&action=%s&menu_id=%s" % (
                article.id,
                request.env.ref('knowledge.knowledge_article_dashboard_action').id,
                request.env.ref('knowledge.knowledge_menu_root').id
            ))
        return request.render('knowledge.knowledge_article_view_frontend', self._prepare_article_frontend_values(article, **post))

    @http.route('/article/toggle_favourite', type='json', auth='user')
    def article_toggle_favourite(self, article_id, **post):
        article = request.env['knowledge.article'].browse(article_id)
        if not article.exists():
            return werkzeug.exceptions.NotFound()
        article = article.sudo()
        if not article.user_has_access:
            return werkzeug.exceptions.Forbidden()
        article.is_user_favourite = not article.is_user_favourite
        return {
            'id': article.id,
            'name': article.display_name,
            'icon': article.icon,
            'is_favourite': article.is_user_favourite,
        }

    def _prepare_article_frontend_values(self, article, **post):
        values = {'article': article}
        values.update(self.get_tree_values(article.id))
        return values

    # ------------------------
    # Articles tree generation
    # ------------------------

    def get_tree_values(self, res_id=False, parent_id=False):
        # sudo article to avoid access error on member or on article for external users.
        # The article the user can see will be based on user_has_access.
        Article = request.env["knowledge.article"].sudo()

        main_articles = Article.search([("parent_id", "=", parent_id), ('user_has_access', '=', True)]).sorted('sequence')
        if parent_id:
            return {'articles': main_articles}

        values = {
            "active_article_id": res_id,
            "favourites": Article.search([("favourite_user_ids", "in", [request.env.user.id]), ('user_has_access', '=', True)]),
            "public_articles": main_articles.filtered(lambda article: article.category == 'workspace'),
            "shared_articles": main_articles.filtered(lambda article: article.category == 'shared'),
        }

        if request.env.user.has_group('base.group_user'):
            values['private_articles'] = main_articles.filtered(lambda article: article.owner_id == request.env.user)
        else:
            values['hide_private'] = True

        return values

    @http.route('/knowledge/get_tree', type='json', auth='user')
    def display_tree(self, res_id=False):
        # TODO: remove res_id and highlight active id after adding the template to the view. ??
        template = request.env.ref('knowledge.knowledge_article_tree_template')._render(self.get_tree_values(res_id=res_id))
        return template

    @http.route('/knowledge/get_children', type='json', auth='user')
    def display_children(self, parent_id):
        template = request.env.ref('knowledge.articles_template')._render(self.get_tree_values(parent_id=parent_id))
        return template