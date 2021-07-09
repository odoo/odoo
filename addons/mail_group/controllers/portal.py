# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import http, fields, tools
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.http import request
from odoo.osv import expression


class PortalMailGroup(http.Controller):
    _thread_per_page = 20
    _replies_per_page = 5

    def _get_archives(self, group_id):
        """Return the different date range and message count for the group messages."""
        results = request.env['mail.group.message']._read_group_raw(
            [('mail_group_id', '=', group_id)],
            ['subject', 'create_date'],
            groupby=['create_date'], orderby='create_date DESC')

        groups = []

        for result in results:
            (dates_range, label) = result['create_date']
            start, end = dates_range.split('/')

            groups.append({
                'date': label,
                'date_begin': fields.Date.to_string(fields.Date.to_date(start)),
                'date_end': fields.Date.to_string(fields.Date.to_date(end)),
                'messages_count': result['create_date_count'],
            })

        return groups

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

        domain = [('mail_group_id', '=', group.id)]
        if mode == 'thread':
            domain += [('group_message_parent_id', '=', False)]

        if date_begin and date_end:
            domain += [('create_date', '>=', date_begin), ('create_date', '<=', date_end)]

        messages = GroupMessage.search(
            domain, limit=self._thread_per_page,
            offset=(page - 1) * self._thread_per_page,
            order='create_date, id DESC')

        pager = portal_pager(
            url=f'/groups/{slug(group)}',
            total=GroupMessage.search_count(domain),
            page=page,
            step=self._thread_per_page,
            scope=5,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'mode': mode}
        )

        return request.render('mail_group.group_messages', {
            'group': group,
            'messages': messages,
            'archives': self._get_archives(group.id),
            'date_begin': date_begin,
            'date_end': date_end,
            'pager': pager,
            'replies_per_page': self._replies_per_page,
        })

    @http.route('/groups/<model("mail.group"):group>/<model("mail.group.message"):message>',
                type='http', auth='public', sitemap=True, website=True)
    def group_view_message(self, group, message, mode='thread', date_begin=None, date_end=None, **post):
        if group != message.mail_group_id:
            raise werkzeug.exceptions.NotFound()

        GroupMessage = request.env['mail.group.message']
        base_domain = [
            ('mail_group_id', '=', group.id),
            ('group_message_parent_id', '=', message.group_message_parent_id.id),
        ]

        next_message = GroupMessage.search(
            expression.AND([base_domain, [('id', '>', message.id)]]),
            order='id ASC', limit=1)
        prev_message = GroupMessage.search(
            expression.AND([base_domain, [('id', '<', message.id)]]),
            order='id DESC', limit=1)

        # Handle access to attachments for public / portal
        if request.env.user.has_group('base.group_user'):
            attachments = message.attachment_ids
        else:
            attachments = message.sudo().attachment_ids
            attachments.generate_access_token()

        values = {
            'message': message,
            'attachments': attachments,
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

        replies_domain = [('id', '>', int(last_displayed_id)), ('group_message_parent_id', '=', message.id)]
        messages = request.env['mail.group.message'].search(replies_domain, limit=self._replies_per_page)
        message_count = request.env['mail.group.message'].search_count(replies_domain)

        if not messages:
            return

        values = {
            'group': group,
            'parent_message': message,
            'messages': messages,
            'msg_more_count': message_count - self._replies_per_page,
            'replies_per_page': self._replies_per_page,
        }
        return request.env.ref('mail_group.messages_short')._render(values, engine='ir.qweb')

    # ------------------------------------------------------------
    # SUBSCRIPTION
    # ------------------------------------------------------------

    @http.route('/groups/subscription', type='json', auth='public', website=True)
    def group_subscribe(self, group_id=0, action='subscribe', email=None, token=None, **kw):
        """Subscribe the current logged user or the given email address to the mailing list.

        If the user is logged, the action is automatically done.

        But if the user is not logged (public user) an email will be send with a token
        to confirm the action.

        :param group_id: Id of the group
        :param action: Action to perform (subscribe or unsubscribe)
        :param email: Email to add in the member list
        :param token: An access token to bypass the <mail.group> access rule
        :return:
            'added'
                if the mmeber was added in the mailing list
            'removed'
                if the member was removed from the mailing list
            'email_sent'
                if we send a confirmation email
            'is_already_member'
                if we try to subscribe but we are already member
            'is_not_member'
                if we try to unsubscribe but we are not member
        """
        if action not in ('subscribe', 'unsubscribe'):
            raise werkzeug.exceptions.NotFound()

        group = request.env['mail.group'].browse(int(group_id)).exists()
        if not group:
            raise werkzeug.exceptions.NotFound()

        # SUDO to have access to field of the many2one
        group_sudo = group.sudo()

        if token and token != group_sudo._generate_group_access_token():
            raise werkzeug.exceptions.NotFound()

        elif not token:
            # Check that the current user has access to the group
            group.check_access_rights('read')
            group.check_access_rule('read')

        partner_id = None
        if not request.env.user._is_public():
            partner_id = request.env.user.partner_id.id

        is_member = bool(group_sudo._find_member(email, partner_id))
        if action == 'subscribe' and is_member:
            return 'is_already_member'
        elif action == 'unsubscribe' and not is_member:
            return 'is_not_member'

        if not request.env.user._is_public():
            # For logged user, automatically join / leave without sending a confirmation email
            if action == 'subscribe':
                group_sudo._join_group(request.env.user.email, partner_id)
                return 'added'
            else:
                group_sudo._leave_group(request.env.user.email, partner_id)
                return 'removed'
        else:
            # For non-logged user, send an email with a token to confirm the action
            if action == 'subscribe':
                group_sudo._send_subscribe_confirmation_email(email, action)
            else:
                group_sudo._send_unsubscribe_confirmation_email(email, action)
            return 'email_sent'

    @http.route('/groups/subscribe', type='http', auth='public', website=True)
    def groups_subscribe_confirm(self, group_id, email, token, action, **kw):
        """Confirm the subscribe / unsubscribe action which was sent by email."""
        if action not in ('subscribe', 'unsubscribe'):
            raise werkzeug.exceptions.NotFound()

        # Here we can SUDO because the token will be checked
        group = request.env['mail.group'].browse(int(group_id)).exists().sudo()
        if not group:
            raise werkzeug.exceptions.NotFound()

        excepted_token = group._generate_action_token(email, action)

        if token != excepted_token:
            return request.render('mail_group.invalid_token_subscription')

        partners = request.env['mail.thread'].sudo()._mail_find_partner_from_emails([email])
        partner_id = partners[0].id if partners else None
        if action == 'subscribe':
            group._join_group(email, partner_id)
        else:
            group._leave_group(email, partner_id)

        return request.render('mail_group.confirmation_subscription', {'subscribing': action == 'subscribe'})
