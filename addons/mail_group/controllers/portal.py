# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import http, fields, tools
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.exceptions import AccessError
from odoo.http import request, Response
from odoo.osv import expression
from odoo.tools import consteq


class PortalMailGroup(http.Controller):
    _thread_per_page = 20
    _replies_per_page = 5

    def _get_website_domain(self):
        # Base group domain in addition to the security access rules
        # Do not show rejected message on the portal view even for admin
        return [('moderation_status', '!=', 'rejected')]

    def _get_archives(self, group_id):
        """Return the different date range and message count for the group messages."""
        domain = expression.AND([self._get_website_domain(), [('mail_group_id', '=', group_id)]])
        results = request.env['mail.group.message']._read_group_raw(
            domain,
            ['subject', 'create_date'],
            groupby=['create_date'], orderby='create_date')

        date_groups = []

        for result in results:
            (dates_range, label) = result['create_date']
            start, end = dates_range.split('/')

            date_groups.append({
                'date': label,
                'date_begin': fields.Date.to_string(fields.Date.to_date(start)),
                'date_end': fields.Date.to_string(fields.Date.to_date(end)),
                'messages_count': result['create_date_count'],
            })

        thread_domain = expression.AND([domain, [('group_message_parent_id', '=', False)]])
        threads_count = request.env['mail.group.message'].search_count(thread_domain)

        return {
            'threads_count': threads_count,
            'threads_time_data': date_groups,
        }

    # ------------------------------------------------------------
    # MAIN PAGE
    # ------------------------------------------------------------

    @http.route('/groups', type='http', auth='public', sitemap=True, website=True)
    def groups_index(self, email='', **kw):
        """View of the group lists. Allow the users to subscribe and unsubscribe."""
        if kw.get('group_id') and kw.get('token'):
            group_id = int(kw.get('group_id'))
            token = kw.get('token')
            group = request.env['mail.group'].browse(group_id).exists().sudo()
            if not group:
                raise werkzeug.exceptions.NotFound()

            if token != group._generate_group_access_token():
                raise werkzeug.exceptions.NotFound()

            mail_groups = group

        else:
            mail_groups = request.env['mail.group'].search([]).sudo()

        if not request.env.user._is_public():
            # Force the email if the user is logged
            email_normalized = request.env.user.email_normalized
            partner_id = request.env.user.partner_id.id
        else:
            email_normalized = tools.email_normalize(email)
            partner_id = None

        members_data = mail_groups._find_members(email_normalized, partner_id)

        return request.render('mail_group.mail_groups', {
            'mail_groups': [{
                'group': group,
                'is_member': bool(members_data.get(group.id, False)),
            } for group in mail_groups],
            'email': email_normalized,
            'is_mail_group_manager': request.env.user.has_group('mail_group.group_mail_group_manager'),
        })

    # ------------------------------------------------------------
    # THREAD DISPLAY / MANAGEMENT
    # ------------------------------------------------------------

    @http.route([
        '/groups/<model("mail.group"):group>',
        '/groups/<model("mail.group"):group>/page/<int:page>',
    ], type='http', auth='public', sitemap=True, website=True)
    def group_view_messages(self, group, page=1, mode='thread', date_begin=None, date_end=None, **post):
        GroupMessage = request.env['mail.group.message']

        domain = expression.AND([self._get_website_domain(), [('mail_group_id', '=', group.id)]])
        if mode == 'thread':
            domain = expression.AND([domain, [('group_message_parent_id', '=', False)]])

        if date_begin and date_end:
            domain = expression.AND([domain, [('create_date', '>', date_begin), ('create_date', '<=', date_end)]])

        # SUDO after the search to apply access rules but be able to read attachments
        messages_sudo = GroupMessage.search(
            domain, limit=self._thread_per_page,
            offset=(page - 1) * self._thread_per_page).sudo()

        pager = portal_pager(
            url=f'/groups/{slug(group)}',
            total=GroupMessage.search_count(domain),
            page=page,
            step=self._thread_per_page,
            scope=5,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'mode': mode}
        )

        self._generate_attachments_access_token(messages_sudo)

        return request.render('mail_group.group_messages', {
            'page_name': 'groups',
            'group': group,
            'messages': messages_sudo,
            'archives': self._get_archives(group.id),
            'date_begin': date_begin,
            'date_end': date_end,
            'pager': pager,
            'replies_per_page': self._replies_per_page,
            'mode': mode,
        })

    @http.route('/groups/<model("mail.group"):group>/<model("mail.group.message"):message>',
                type='http', auth='public', sitemap=False, website=True)
    def group_view_message(self, group, message, mode='thread', date_begin=None, date_end=None, **post):
        if group != message.mail_group_id:
            raise werkzeug.exceptions.NotFound()

        GroupMessage = request.env['mail.group.message']
        base_domain = expression.AND([
            self._get_website_domain(),
            [('mail_group_id', '=', group.id),
             ('group_message_parent_id', '=', message.group_message_parent_id.id)],
        ])

        next_message = GroupMessage.search(
            expression.AND([base_domain, [('id', '>', message.id)]]),
            order='id ASC', limit=1)
        prev_message = GroupMessage.search(
            expression.AND([base_domain, [('id', '<', message.id)]]),
            order='id DESC', limit=1)

        message_sudo = message.sudo()
        self._generate_attachments_access_token(message_sudo)

        values = {
            'page_name': 'groups',
            'message': message_sudo,
            'group': group,
            'mode': mode,
            'archives': self._get_archives(group.id),
            'date_begin': date_begin,
            'date_end': date_end,
            'replies_per_page': self._replies_per_page,
            'next_message': next_message,
            'prev_message': prev_message,
        }
        return request.render('mail_group.group_message', values)

    @http.route('/groups/<model("mail.group"):group>/<model("mail.group.message"):message>/get_replies',
                type='json', auth='public', methods=['POST'], website=True)
    def group_message_get_replies(self, group, message, last_displayed_id, **post):
        if group != message.mail_group_id:
            raise werkzeug.exceptions.NotFound()

        replies_domain = expression.AND([
            self._get_website_domain(),
            [('id', '>', int(last_displayed_id)), ('group_message_parent_id', '=', message.id)],
        ])
        # SUDO after the search to apply access rules but be able to read attachments
        replies_sudo = request.env['mail.group.message'].search(replies_domain, limit=self._replies_per_page).sudo()
        message_count = request.env['mail.group.message'].search_count(replies_domain)

        if not replies_sudo:
            return

        message_sudo = message.sudo()

        self._generate_attachments_access_token(message_sudo | replies_sudo)

        values = {
            'group': group,
            'parent_message': message_sudo,
            'messages': replies_sudo,
            'msg_more_count': message_count - self._replies_per_page,
            'replies_per_page': self._replies_per_page,
        }
        return request.env['ir.qweb']._render('mail_group.messages_short', values)

    # ------------------------------------------------------------
    # SUBSCRIPTION
    # ------------------------------------------------------------

    # csrf is disabled here because it will be called by the MUA with unpredictable session at that time
    @http.route('/group/<int:group_id>/unsubscribe_oneclick', website=True, type='http', auth='public',
           methods=['POST'], csrf=False)
    def group_unsubscribe_oneclick(self, group_id, token, email):
        """ Unsubscribe a given user from a given group. One-click unsubscribe
        allow mail user agent to propose a one click button to the user to
        unsubscribe as defined in rfc8058. Only POST method is allowed preventing
        the risk that anti-spam trigger unwanted unsubscribe (scenario explained
        in the same rfc).

        :param int group_id: group ID from which user wants to unsubscribe;
        :param str token: optional access token ensuring security;
        :param email: email to unsubscribe;
        """
        group_sudo = request.env['mail.group'].sudo().browse(group_id).exists()
        # new route parameters
        if group_sudo and token and email:
            correct_token = group_sudo._generate_email_access_token(email)
            if not consteq(correct_token, token):
                raise werkzeug.exceptions.NotFound()
            group_sudo._leave_group(email)
        else:
            raise werkzeug.exceptions.NotFound()
        return Response(status=200)

    @http.route('/group/subscribe', type='json', auth='public', website=True)
    def group_subscribe(self, group_id=0, email=None, token=None, **kw):
        """Subscribe the current logged user or the given email address to the mailing list.

        If the user is logged, the action is automatically done.

        But if the user is not logged (public user) an email will be send with a token
        to confirm the action.

        :param group_id: Id of the group
        :param email: Email to add in the member list
        :param token: An access token to bypass the <mail.group> access rule
        :return:
            'added'
                if the member was added in the mailing list
            'email_sent'
                if we send a confirmation email
            'is_already_member'
                if we try to subscribe but we are already member
        """
        group_sudo, is_member, partner_id = self._group_subscription_get_group(group_id, email, token)

        if is_member:
            return 'is_already_member'

        if not request.env.user._is_public():
            # For logged user, automatically join / leave without sending a confirmation email
            group_sudo._join_group(request.env.user.email, partner_id)
            return 'added'

        # For non-logged user, send an email with a token to confirm the action
        group_sudo._send_subscribe_confirmation_email(email)
        return 'email_sent'

    @http.route('/group/unsubscribe', type='json', auth='public', website=True)
    def group_unsubscribe(self, group_id=0, email=None, token=None, **kw):
        """Unsubscribe the current logged user or the given email address to the mailing list.

        If the user is logged, the action is automatically done.

        But if the user is not logged (public user) an email will be send with a token
        to confirm the action.

        :param group_id: Id of the group
        :param email: Email to add in the member list
        :param token: An access token to bypass the <mail.group> access rule
        :return:
            'removed'
                if the member was removed from the mailing list
            'email_sent'
                if we send a confirmation email
            'is_not_member'
                if we try to unsubscribe but we are not member
        """
        group_sudo, is_member, partner_id = self._group_subscription_get_group(group_id, email, token)

        if not is_member:
            return 'is_not_member'

        if not request.env.user._is_public():
            # For logged user, automatically join / leave without sending a confirmation email
            group_sudo._leave_group(request.env.user.email, partner_id)
            return 'removed'

        # For non-logged user, send an email with a token to confirm the action
        group_sudo._send_unsubscribe_confirmation_email(email)
        return 'email_sent'

    def _group_subscription_get_group(self, group_id, email, token):
        """Check the given token and return,

        :return:
            - The group sudo-ed
            - True if the email is member of the group
            - The partner of the current user
        :raise NotFound: if the given token is not valid
        """
        group = request.env['mail.group'].browse(int(group_id)).exists()
        if not group:
            raise werkzeug.exceptions.NotFound()

        # SUDO to have access to field of the many2one
        group_sudo = group.sudo()

        if token and token != group_sudo._generate_group_access_token():
            raise werkzeug.exceptions.NotFound()

        elif not token:
            try:
                # Check that the current user has access to the group
                group.check_access_rights('read')
                group.check_access_rule('read')
            except AccessError:
                raise werkzeug.exceptions.NotFound()

        partner_id = None
        if not request.env.user._is_public():
            partner_id = request.env.user.partner_id.id

        is_member = bool(group_sudo._find_member(email, partner_id))

        return group_sudo, is_member, partner_id

    @http.route('/group/subscribe-confirm', type='http', auth='public', website=True)
    def group_subscribe_confirm(self, group_id, email, token, **kw):
        """Confirm the subscribe / unsubscribe action which was sent by email."""
        group = self._group_subscription_confirm_get_group(group_id, email, token, 'subscribe')
        if not group:
            return request.render('mail_group.invalid_token_subscription')

        partners = request.env['mail.thread'].sudo()._mail_find_partner_from_emails([email])
        partner_id = partners[0].id if partners else None
        group._join_group(email, partner_id)

        return request.render('mail_group.confirmation_subscription', {
            'group': group,
            'email': email,
            'subscribing': True,
        })

    @http.route('/group/unsubscribe-confirm', type='http', auth='public', website=True)
    def group_unsubscribe_confirm(self, group_id, email, token, **kw):
        """Confirm the subscribe / unsubscribe action which was sent by email."""
        group = self._group_subscription_confirm_get_group(group_id, email, token, 'unsubscribe')
        if not group:
            return request.render('mail_group.invalid_token_subscription')

        group._leave_group(email, all_members=True)

        return request.render('mail_group.confirmation_subscription', {
            'group': group,
            'email': email,
            'subscribing': False,
        })

    def _group_subscription_confirm_get_group(self, group_id, email, token, action):
        """Retrieve the group and check the token use to perform the given action."""
        if not group_id or not email or not token:
            return False
        # Here we can SUDO because the token will be checked
        group = request.env['mail.group'].browse(int(group_id)).exists().sudo()
        if not group:
            raise werkzeug.exceptions.NotFound()

        excepted_token = group._generate_action_token(email, action)
        return group if token == excepted_token else False

    def _generate_attachments_access_token(self, messages):
        for message in messages:
            if message.attachment_ids:
                message.attachment_ids.generate_access_token()
            self._generate_attachments_access_token(message.group_message_child_ids)
