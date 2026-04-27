# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import conf, http, tools, _
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
        if request.env.user._is_internal():
            return self._redirect_to_backend_view(article)
        return self._redirect_to_portal_view(article)

    @http.route('/knowledge/article/<int:article_id>', type='http', auth='user')
    def redirect_to_article(self, article_id, show_resolved_threads=False):
        """ This route will redirect internal users to the backend view of the
        article and the share users to the frontend view instead."""
        article = request.env['knowledge.article'].with_context(active_test=False).search([('id', '=', article_id)])
        if not article:
            return werkzeug.exceptions.Forbidden()

        if request.env.user._is_internal():
            return self._redirect_to_backend_view(article, show_resolved_threads)
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

    def _redirect_to_backend_view(self, article, show_resolved_threads=False):
        if article.id and show_resolved_threads:
            action_id = request.env.ref('knowledge.knowledge_article_action_form_show_resolved').id
            return request.redirect(f'/odoo/action-{action_id}/{article.id}')
        return request.redirect(f'/odoo/knowledge/{article.id or "new"}')

    def _redirect_to_portal_view(self, article):
        # We build the session information necessary for the web client to load
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context)
        mods = conf.server_wide_modules or []
        lang = user_context.get("lang")
        cache_hashes = {
            "translations": request.env['ir.http'].get_web_translations_hash(mods, lang),
        }

        session_info.update(
            cache_hashes=cache_hashes,
            user_companies={
                'current_company': request.env.company.id,
                'allowed_companies': {
                    request.env.company.id: {
                        'id': request.env.company.id,
                        'name': request.env.company.name,
                    },
                },
            },
        )

        return request.render(
            'knowledge.knowledge_portal_view',
            {'session_info': session_info},
        )

    # ------------------------
    # Article permission panel
    # ------------------------

    @http.route('/knowledge/get_article_permission_panel_data', type='json', auth='user')
    def get_article_permission_panel_data(self, article_id):
        """
        Returns a dictionary containing all values required to render the permission panel.
        :param article_id: (int) article id
        """
        article = request.env['knowledge.article'].search([('id', '=', article_id)])
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

        based_on_articles = request.env['knowledge.article'].search([
            ('id', 'in', list(set(member['based_on'] for member in members_permission.values() if member['based_on'])))
        ])

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
                'partner_email': member['partner_email'] if not member['partner_share'] or partner_id == request.env.user.partner_id.id or request.env.user._is_internal() else False,
                'permission': member['permission'],
                'based_on': f'{member["based_on_icon"] or request.env["knowledge.article"]._get_no_icon_placeholder()} {member["based_on_name"] or _("Untitled")}' if member['based_on'] else False,
                'based_on_id': member['based_on'] if member['based_on'] in based_on_articles.ids else False,
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
        parent_article_sudo = article.parent_id.sudo()
        inherited_permission_parent_sudo = article.inherited_permission_parent_id.sudo()

        return {
            'internal_permission_options': sorted(internal_permission_field.get_description(request.env).get('selection', []),
                                                  key=lambda x: x[0] == article.inherited_permission, reverse=True),
            'internal_permission': article.inherited_permission,
            'category': article.category,
            'parent_permission': parent_article_sudo.inherited_permission,
            'based_on': inherited_permission_parent_sudo.display_name,
            'based_on_id': inherited_permission_parent_sudo.id if inherited_permission_parent_sudo.user_has_access else False,
            'members_options': permission_field.get_description(request.env).get('selection', []),
            'members': members_values,
            'is_sync': is_sync,
            'parent_id': parent_article_sudo.id if parent_article_sudo.user_has_access else False,
            'parent_name': parent_article_sudo.display_name,
            'user_is_admin': user_is_admin,
            'show_admin_tip': user_is_admin and article.user_permission != 'write',
        }

    @http.route('/knowledge/article/set_member_permission', type='json', auth='user')
    def article_set_member_permission(self, article_id, permission, member_id=False, inherited_member_id=False):
        """ Sets the permission of the given member for the given article.

        The returned result can also include a `new_category` entry that tells the
        caller that the article changed category.

        **Note**: The user needs "write" permission to change the permission of a user.

        :param int article_id: target article id;
        :param string permission: permission to set on member, one of 'none',
          'read' or 'write';
        :param int member_id: id of a member of the given article;
        :param int inherited_member_id: id of a member from one of the article's
          parent (indicates rights are inherited from parents);
        """
        article = request.env['knowledge.article'].search([('id', '=', article_id)])
        if not article:
            return werkzeug.exceptions.Forbidden()
        member = request.env['knowledge.article.member'].browse(member_id or inherited_member_id).exists()
        if not member:
            return {'error': _("The selected member does not exists or has been already deleted.")}

        previous_category = article.category

        try:
            article._set_member_permission(member, permission, bool(inherited_member_id))
        except (AccessError, ValidationError):
            return {'error': _("You cannot change the permission of this member.")}

        if article.category != previous_category:
            return {'new_category': True}

        return {}

    @http.route('/knowledge/article/remove_member', type='json', auth='user')
    def article_remove_member(self, article_id, member_id=False, inherited_member_id=False):
        """ Removes the given member from the given article.

        The returned result can also include a `new_category` entry that tells the
        caller that the article changed category.

        **Note**: The user needs "write" permission to remove another member from
        the list. The user can always remove themselves from the list.

        :param int article_id: target article id;
        :param int member_id: id of a member of the given article;
        :param int inherited_member_id: id of a member from one of the article's
          parent (indicates rights are inherited from parents);
        """
        article = request.env['knowledge.article'].search([('id', '=', article_id)])
        if not article:
            return werkzeug.exceptions.Forbidden()
        member = request.env['knowledge.article.member'].browse(member_id or inherited_member_id).exists()
        if not member:
            return {'error': _("The selected member does not exists or has been already deleted.")}

        previous_category = article.category
        partner = member.partner_id

        try:
            article._remove_member(member)
        except (AccessError, ValidationError) as e:
            return {'error': e}

        if partner == request.env.user.partner_id and article.category == 'private':
            # When leaving private article, the article will be archived instead
            # As a result, user won't see the article anymore and the home page
            # should be fully reloaded to open the first 'available' article.
            return {'reload_all': True}

        if article.category != previous_category:
            return {'new_category': True}

        return {}

    @http.route('/knowledge/article/set_internal_permission', type='json', auth='user')
    def article_set_internal_permission(self, article_id, permission):
        """ Sets the internal permission of the given article.

        The returned result can also include a `new_category` entry that tells the
        caller that the article changed category.

        **Note**: The user needs "write" permission to update the internal permission
        of the article.

        :param int article_id: target article id;
        :param string permission: permission to set on member, one of 'none',
          'read' or 'write';
        """
        article = request.env['knowledge.article'].search([('id', '=', article_id)])
        if not article:
            return werkzeug.exceptions.Forbidden()

        previous_category = article.category

        try:
            article._set_internal_permission(permission)
        except (AccessError, ValidationError):
            return {'error': _("You cannot change the internal permission of this article.")}

        if article.category != previous_category:
            return {'new_category': True}

        return {}
