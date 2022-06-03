# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import http, tools, _
from odoo.exceptions import AccessError, ValidationError
from odoo.http import request


class KnowledgeController(http.Controller):

    # ------------------------
    # Article Access Routes
    # ------------------------

    @http.route('/knowledge/home', type='http', auth='user')
    def access_knowledge_home(self):
        """ This route will redirect internal users to the backend view of the
        article and the share users to the frontend view instead. """
        article = request.env["knowledge.article"]._get_first_accessible_article()
        if request.env.user.has_group('base.group_user') and not article:
            return self._redirect_to_backend_view(article)
        if not article:
            return self._redirect_to_portal_view(False, hide_side_bar=True)
        return request.redirect("/knowledge/article/%s" % article.id)

    @http.route('/knowledge/article/<int:article_id>', type='http', auth='user')
    def redirect_to_article(self, article_id):
        """ This route will redirect internal users to the backend view of the
        article and the share users to the frontend view instead."""
        article = self._fetch_article(article_id)
        if request.env.user.has_group('base.group_user'):
            if not article:
                return werkzeug.exceptions.Forbidden()
            return self._redirect_to_backend_view(article)
        return self._redirect_to_portal_view(article)

    @http.route('/knowledge/article/invite/<int:member_id>/<string:invitation_hash>', type='http', auth='public')
    def article_invite(self, member_id, invitation_hash):
        """ This route will check if the given parameter allows the client to access the article via the invite token.
        Then, if the partner has not registered yet, we will redirect the client to the signup page to finally redirect
        them to the article.
        If the partner already has registrered, we redirect them directly to the article.
        """
        member = request.env['knowledge.article.member'].sudo().browse(member_id).exists()
        correct_token = member._get_invitation_hash() if member else False
        if not correct_token or not tools.consteq(correct_token, invitation_hash):
            raise werkzeug.exceptions.NotFound()

        partner = member.partner_id
        article = member.article_id

        if not partner.user_ids:
            # Force the signup even if not enabled (as we explicitly invited the member).
            # They should still be able to create a user.
            signup_allowed = request.env['res.users']._get_signup_invitation_scope() == 'b2c'
            if not signup_allowed:
                partner.signup_prepare()
            partner.signup_get_auth_param()
            signup_url = partner._get_signup_url_for_action(url='/knowledge/article/%s' % article.id)[partner.id]
            return request.redirect(signup_url)

        return request.redirect('/web/login?redirect=/knowledge/article/%s' % article.id)

    def _fetch_article(self, article_id):
        """ Check the access of the given article for the current user. """
        article = request.env['knowledge.article'].browse(int(article_id)).exists()
        if not article:
            return request.env['knowledge.article']
        try:
            article.check_access_rights('read')
            article.check_access_rule('read')
        except AccessError:
            return request.env['knowledge.article']
        return article

    def _redirect_to_backend_view(self, article):
        return request.redirect("/web#id=%s&model=knowledge.article&action=%s&menu_id=%s" % (
            article.id if article else '',
            request.env.ref("knowledge.knowledge_article_action_form").id,
            request.env.ref('knowledge.knowledge_menu_root').id
        ))

    def _redirect_to_portal_view(self, article, hide_side_bar=False):
        return request.render('knowledge.knowledge_article_view_frontend', {
            'article': article,
            'portal_readonly_mode': True,  # used to bypass access check (to speed up loading)
            'show_sidebar': not hide_side_bar and bool(self._get_root_articles(limit=1))
        })

    # ------------------------
    # Articles tree generation
    # ------------------------

    def _get_root_articles(self, limit=None):
        """ Meant to be overriden by website_knowledge to search in sudo with adapted domain."""
        _order = 'sequence' if limit is not None else None
        return request.env["knowledge.article"].search([("parent_id", "=", False)], limit=limit, order=_order)

    def _prepare_articles_tree_html(self, template, active_article, unfolded_articles=False):
        """ Prepares all the info needed to render the article tree view side panel
        and returns the rendered given template with those values.

        :param <knowledge.article> active_article: used to highlight the given
          article_id in the template;
        :param list unfolded_articles: List of IDs used to display the children
          of the given article ids. Unfolded articles are saved into local storage.
          When reloading/opening the article page, previously unfolded articles
          nodes must be opened;
        """
        unfolded_articles = set() if not unfolded_articles else set(unfolded_articles)
        if active_article:
            # root articles = starting point of the tree view : unfold only if root_article in (accessible) parents
            ancestors = active_article._get_readable_ancetors()
            if active_article.root_article_id in ancestors:
                unfolded_articles |= set(ancestors.ids)

        root_articles = self._get_root_articles()

        values = {
            "active_article": active_article,
            "workspace_articles": root_articles.filtered(lambda article: article.category == 'workspace'),
            "shared_articles": root_articles.filtered(lambda article: article.category == 'shared'),
            "private_articles": root_articles.filtered(
                lambda article: article.category == "private" and article.user_has_write_access),
            "unfolded_articles": unfolded_articles,
            'portal_readonly_mode': not request.env.user.has_group('base.group_user'),
        }
        favorites = request.env['knowledge.article.favorite']
        if not request.env.user._is_public():
            favorites = request.env['knowledge.article.favorite'].search([
                ("user_id", "=", request.env.user.id), ('article_id.active', '=', True)
            ])
        values["favorites"] = favorites

        return request.env['ir.qweb']._render(template, values)

    @http.route('/knowledge/tree_panel', type='json', auth='user')
    def get_tree_panel_all(self, active_article_id=False, unfolded_articles=False):
        return self._prepare_articles_tree_html(
            'knowledge.knowledge_article_tree',
            self._fetch_article(active_article_id),
            unfolded_articles=unfolded_articles
        )

    @http.route('/knowledge/tree_panel/portal', type='json', auth='public')
    def get_tree_panel_portal(self, active_article_id=False, unfolded_articles=False):
        """ Frontend access for left panel. """
        return self._prepare_articles_tree_html(
            'knowledge.knowledge_article_tree_frontend',
            self._fetch_article(active_article_id),
            unfolded_articles=unfolded_articles
        )

    @http.route('/knowledge/tree_panel/children', type='json', auth='user')
    def get_tree_panel_children(self, parent_id):
        parent = self._fetch_article(parent_id)
        if not parent:
            return werkzeug.exceptions.NotFound()
        return request.env['ir.qweb']._render('knowledge.articles_template', {
            'articles': parent.child_ids,
            'portal_readonly_mode': not request.env.user.has_group('base.group_user'),  # used to bypass access check (to speed up loading)
        })

    @http.route('/knowledge/tree_panel/favorites', type='json', auth='user')
    def get_tree_panel_favorites(self, active_article_id=False):
        favorite_articles = request.env['knowledge.article.favorite'].search([
            ("user_id", "=", request.env.user.id), ('article_id.active', '=', True)
        ])
        return request.env['ir.qweb']._render('knowledge.knowledge_article_tree_favorites', {
            'favorites': favorite_articles,
            "active_article": request.env['knowledge.article'].browse(active_article_id),
        })

    # ------------------------
    # Article permission panel
    # ------------------------

    @http.route('/knowledge/get_article_permission_panel_data', type='json', auth='user')
    def get_article_permission_panel_data(self, article_id):
        """
        Returns a dictionnary containing all values required to render the permission panel.
        :param article_id: (int) article id
        """
        article = self._fetch_article(article_id)
        if not article:
            return werkzeug.exceptions.Forbidden()
        is_sync = not article.is_desynchronized
        # Get member permission info
        members_values = []
        members_permission = article._get_article_member_permissions(additional_fields={
            'res.partner': [
                ('name', 'partner_name'),
                ('email', 'partner_email'),
                ('partner_share', 'partner_share'),
            ],
            'knowledge.article': [
                ('icon', 'based_on_icon'),
                ('name', 'based_on_name'),
            ],
        })[article.id]
        for partner_id, member in members_permission.items():
            # empty member added by '_get_article_member_permissions', don't show it in the panel
            if not member['member_id']:
                continue

            # if share partner and permission = none, don't show it in the permission panel.
            if member['permission'] == 'none' and member['partner_share']:
                continue

            # if article is desyncronized, don't show members based on parent articles.
            if not is_sync and member['based_on']:
                continue

            member_values = {
                'id': member['member_id'],
                'partner_id': partner_id,
                'partner_name': member['partner_name'],
                'partner_email': member['partner_email'],
                'permission': member['permission'],
                'based_on': f'{member["based_on_icon"] or "📄"} {member["based_on_name"]}' if member['based_on_name'] else False,
                'based_on_id': member['based_on'],
                'partner_share': member['partner_share'],
                'is_unique_writer': member['permission'] == "write" and article.inherited_permission != "write" and not any(
                    other_member['permission'] == 'write'
                    for partner_id, other_member in members_permission.items()
                    if other_member['member_id'] != member['member_id']
                ),
            }
            members_values.append(member_values)

        internal_permission_field = request.env['knowledge.article']._fields['internal_permission']
        permission_field = request.env['knowledge.article.member']._fields['permission']
        user_is_admin = request.env.user._is_admin()
        return {
            'internal_permission_options': internal_permission_field.get_description(request.env).get('selection', []),
            'internal_permission': article.inherited_permission,
            'parent_permission': article.parent_id.inherited_permission,
            'based_on': article.inherited_permission_parent_id.display_name,
            'based_on_id': article.inherited_permission_parent_id.id,
            'members_options': permission_field.get_description(request.env).get('selection', []),
            'members': members_values,
            'is_sync': is_sync,
            'parent_id': article.parent_id.id,
            'parent_name': article.parent_id.display_name,
            'user_is_admin': user_is_admin,
            'show_admin_tip': user_is_admin and article.user_permission != 'write',
        }

    @http.route('/knowledge/article/set_member_permission', type='json', auth='user')
    def article_set_member_permission(self, article_id, permission, member_id=False, inherited_member_id=False):
        """ Sets the permission of the given member for the given article.

        The returned result can also include a `reload_tree` entry that tells the
        caller that the aside block listing all articles should be reloaded. This
        happens when the article moves from one section to another.

        **Note**: The user needs "write" permission to change the permission of a user.

        :param int article_id: target article id;
        :param string permission: permission to set on member, one of 'none',
          'read' or 'write';
        :param int member_id: id of a member of the given article;
        :param int inherited_member_id: id of a member from one of the article's
          parent (indicates rights are inherited from parents);
        """
        article = self._fetch_article(article_id)
        if not article:
            return werkzeug.exceptions.Forbidden()
        member = request.env['knowledge.article.member'].browse(member_id or inherited_member_id).exists()
        if not member:
            return {'error': _("The selected member does not exists or has been already deleted.")}

        previous_category = article.category

        try:
            article._set_member_permission(member, permission, bool(inherited_member_id))
        except (AccessError, ValidationError):
            return {'error': _("You cannot change the permission if this member.")}

        if article.category != previous_category:
            return {'reload_tree': True}

        return {}

    @http.route('/knowledge/article/remove_member', type='json', auth='user')
    def article_remove_member(self, article_id, member_id=False, inherited_member_id=False):
        """ Removes the given member from the given article.

        The returned result can also include a `reload_tree` entry that tells the
        caller that the aside block listing all articles should be reloaded. This
        happens when the article moves from one section to another.

        **Note**: The user needs "write" permission to remove another member from
        the list. The user can always remove themselves from the list.

        :param int article_id: target article id;
        :param int member_id: id of a member of the given article;
        :param int inherited_member_id: id of a member from one of the article's
          parent (indicates rights are inherited from parents);
        """
        article = self._fetch_article(article_id)
        if not article:
            return werkzeug.exceptions.Forbidden()
        member = request.env['knowledge.article.member'].browse(member_id or inherited_member_id).exists()
        if not member:
            return {'error': _("The selected member does not exists or has been already deleted.")}

        previous_category = article.category

        try:
            article._remove_member(member)
        except (AccessError, ValidationError) as e:
            return {'error': e}

        if article.category != previous_category:
            return {'reload_tree': True}

        return {}

    @http.route('/knowledge/article/set_internal_permission', type='json', auth='user')
    def article_set_internal_permission(self, article_id, permission):
        """ Sets the internal permission of the given article.

        The returned result can also include a `reload_tree` entry that tells the
        caller that the aside block listing all articles should be reloaded. This
        happens when the article moves from one section to another.

        **Note**: The user needs "write" permission to update the internal permission
        of the article.

        :param int article_id: target article id;
        :param string permission: permission to set on member, one of 'none',
          'read' or 'write';
        """
        article = self._fetch_article(article_id)
        if not article:
            return werkzeug.exceptions.Forbidden()

        previous_category = article.category

        try:
            article._set_internal_permission(permission)
        except (AccessError, ValidationError):
            return {'error': _("You cannot change the internal permission of this article.")}

        if article.category != previous_category:
            return {'reload_tree': True}
        return {}
