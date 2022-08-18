# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from collections import defaultdict
from datetime import datetime, timedelta
from psycopg2 import IntegrityError
from psycopg2.errorcodes import UNIQUE_VIOLATION

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import consteq, file_open
from odoo.tools.misc import get_lang
from odoo.tools.translate import _
from werkzeug.exceptions import NotFound


class DiscussController(http.Controller):

    # --------------------------------------------------------------------------
    # Public Pages
    # --------------------------------------------------------------------------

    @http.route([
        '/chat/<string:create_token>',
        '/chat/<string:create_token>/<string:channel_name>',
    ], methods=['GET'], type='http', auth='public')
    def discuss_channel_chat_from_token(self, create_token, channel_name=None, **kwargs):
        return self._response_discuss_channel_from_token(create_token=create_token, channel_name=channel_name)

    @http.route([
        '/meet/<string:create_token>',
        '/meet/<string:create_token>/<string:channel_name>',
    ], methods=['GET'], type='http', auth='public')
    def discuss_channel_meet_from_token(self, create_token, channel_name=None, **kwargs):
        return self._response_discuss_channel_from_token(create_token=create_token, channel_name=channel_name, default_display_mode='video_full_screen')

    @http.route('/chat/<int:channel_id>/<string:invitation_token>', methods=['GET'], type='http', auth='public')
    def discuss_channel_invitation(self, channel_id, invitation_token, **kwargs):
        channel_sudo = request.env['mail.channel'].browse(channel_id).sudo().exists()
        if not channel_sudo or not channel_sudo.uuid or not consteq(channel_sudo.uuid, invitation_token):
            raise NotFound()
        return self._response_discuss_channel_invitation(channel_sudo=channel_sudo)

    @http.route('/discuss/channel/<int:channel_id>', methods=['GET'], type='http', auth='public')
    def discuss_channel(self, channel_id, **kwargs):
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        return self._response_discuss_public_channel_template(channel_sudo=channel_member_sudo.channel_id)

    def _response_discuss_channel_from_token(self, create_token, channel_name=None, default_display_mode=False):
        if not request.env['ir.config_parameter'].sudo().get_param('mail.chat_from_token'):
            raise NotFound()
        channel_sudo = request.env['mail.channel'].sudo().search([('uuid', '=', create_token)])
        if not channel_sudo:
            try:
                channel_sudo = channel_sudo.create({
                    'default_display_mode': default_display_mode,
                    'name': channel_name or create_token,
                    'public': 'public',
                    'uuid': create_token,
                })
            except IntegrityError as e:
                if e.pgcode != UNIQUE_VIOLATION:
                    raise
                # concurrent insert attempt: another request created the channel.
                # commit the current transaction and get the channel.
                request.env.cr.commit()
                channel_sudo = channel_sudo.search([('uuid', '=', create_token)])
        return self._response_discuss_channel_invitation(channel_sudo=channel_sudo, is_channel_token_secret=False)

    def _response_discuss_channel_invitation(self, channel_sudo, is_channel_token_secret=True):
        if channel_sudo.channel_type == 'chat':
            raise NotFound()
        discuss_public_view_data = {
            'isChannelTokenSecret': is_channel_token_secret,
        }
        add_guest_cookie = False
        channel_member_sudo = channel_sudo.env['mail.channel.member']._get_as_sudo_from_request(request=request, channel_id=channel_sudo.id)
        if channel_member_sudo:
            channel_sudo = channel_member_sudo.channel_id  # ensure guest is in context
        else:
            if not channel_sudo.env.user._is_public():
                try:
                    channel_sudo.add_members([channel_sudo.env.user.partner_id.id])
                except UserError:
                    raise NotFound()
            else:
                guest = channel_sudo.env['mail.guest']._get_guest_from_request(request)
                if guest:
                    channel_sudo = channel_sudo.with_context(guest=guest)
                    try:
                        channel_sudo.add_members(guest_ids=[guest.id])
                    except UserError:
                        raise NotFound()
                else:
                    if channel_sudo.public == 'groups':
                        raise NotFound()
                    guest = channel_sudo.env['mail.guest'].create({
                        'country_id': channel_sudo.env['res.country'].search([('code', '=', request.geoip.get('country_code'))], limit=1).id,
                        'lang': get_lang(channel_sudo.env).code,
                        'name': _("Guest"),
                        'timezone': channel_sudo.env['mail.guest']._get_timezone_from_request(request),
                    })
                    add_guest_cookie = True
                    discuss_public_view_data.update({
                        'shouldAddGuestAsMemberOnJoin': True,
                        'shouldDisplayWelcomeViewInitially': True,
                    })
                channel_sudo = channel_sudo.with_context(guest=guest)
        response = self._response_discuss_public_channel_template(channel_sudo=channel_sudo, discuss_public_view_data=discuss_public_view_data)
        if add_guest_cookie:
            # Discuss Guest ID: every route in this file will make use of it to authenticate
            # the guest through `_get_as_sudo_from_request` or `_get_as_sudo_from_request_or_raise`.
            expiration_date = datetime.now() + timedelta(days=365)
            response.set_cookie(guest._cookie_name, f"{guest.id}{guest._cookie_separator}{guest.access_token}", httponly=True, expires=expiration_date)
        return response

    def _response_discuss_public_channel_template(self, channel_sudo, discuss_public_view_data=None):
        discuss_public_view_data = discuss_public_view_data or {}
        return request.render('mail.discuss_public_channel_template', {
            'data': {
                'channelData': channel_sudo.channel_info()[0],
                'discussPublicViewData': dict({
                    'channel': [('insert', {'id': channel_sudo.id, 'model': 'mail.channel'})],
                    'shouldDisplayWelcomeViewInitially': channel_sudo.default_display_mode == 'video_full_screen',
                }, **discuss_public_view_data),
            },
            'session_info': channel_sudo.env['ir.http'].session_info(),
        })

    # --------------------------------------------------------------------------
    # Semi-Static Content (GET requests with possible cache)
    # --------------------------------------------------------------------------

    @http.route('/mail/channel/<int:channel_id>/partner/<int:partner_id>/avatar_128', methods=['GET'], type='http', auth='public')
    def mail_channel_partner_avatar_128(self, channel_id, partner_id, **kwargs):
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request(request=request, channel_id=channel_id)
        partner_sudo = channel_member_sudo.env['res.partner'].browse(partner_id).exists()
        placeholder = partner_sudo._avatar_get_placeholder_path()
        if channel_member_sudo and channel_member_sudo.env['mail.channel.member'].search([('channel_id', '=', channel_id), ('partner_id', '=', partner_id)], limit=1):
            return request.env['ir.binary']._get_image_stream_from(partner_sudo, field_name='avatar_128', placeholder=placeholder).get_response()
        if request.env.user.share:
            return request.env['ir.binary']._get_placeholder_stream(placeholder)
        return request.env['ir.binary']._get_image_stream_from(partner_sudo.sudo(False), field_name='avatar_128', placeholder=placeholder).get_response()

    @http.route('/mail/channel/<int:channel_id>/guest/<int:guest_id>/avatar_128', methods=['GET'], type='http', auth='public')
    def mail_channel_guest_avatar_128(self, channel_id, guest_id, **kwargs):
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request(request=request, channel_id=channel_id)
        guest_sudo = channel_member_sudo.env['mail.guest'].browse(guest_id).exists()
        placeholder = guest_sudo._avatar_get_placeholder_path()
        if channel_member_sudo and channel_member_sudo.env['mail.channel.member'].search([('channel_id', '=', channel_id), ('guest_id', '=', guest_id)], limit=1):
            return request.env['ir.binary']._get_image_stream_from(guest_sudo, field_name='avatar_128', placeholder=placeholder).get_response()
        if request.env.user.share:
            return request.env['ir.binary']._get_placeholder_stream(placeholder)
        return request.env['ir.binary']._get_image_stream_from(guest_sudo.sudo(False), field_name='avatar_128', placeholder=placeholder).get_response()

    @http.route('/mail/channel/<int:channel_id>/attachment/<int:attachment_id>', methods=['GET'], type='http', auth='public')
    def mail_channel_attachment(self, channel_id, attachment_id, download=None, **kwargs):
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        attachment_sudo = channel_member_sudo.env['ir.attachment'].search([
                ('id', '=', int(attachment_id)),
                ('res_id', '=', int(channel_id)),
                ('res_model', '=', 'mail.channel')
            ], limit=1)
        if not attachment_sudo:
            raise NotFound()
        return request.env['ir.binary']._get_stream_from(attachment_sudo).get_response(as_attachment=download)

    @http.route([
        '/mail/channel/<int:channel_id>/image/<int:attachment_id>',
        '/mail/channel/<int:channel_id>/image/<int:attachment_id>/<int:width>x<int:height>',
    ], methods=['GET'], type='http', auth='public')
    def fetch_image(self, channel_id, attachment_id, width=0, height=0, **kwargs):
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        attachment_sudo = channel_member_sudo.env['ir.attachment'].search([
                ('id', '=', int(attachment_id)),
                ('res_id', '=', int(channel_id)),
                ('res_model', '=', 'mail.channel'),
            ], limit=1)

        if not attachment_sudo:
            raise NotFound()

        return request.env['ir.binary']._get_image_stream_from(
            attachment_sudo, width=int(width), height=int(height)
        ).get_response(as_attachment=kwargs.get('download'))

    # --------------------------------------------------------------------------
    # Client Initialization
    # --------------------------------------------------------------------------

    @http.route('/mail/init_messaging', methods=['POST'], type='json', auth='public')
    def mail_init_messaging(self, **kwargs):
        if not request.env.user.sudo()._is_public():
            return request.env.user.sudo(False)._init_messaging()
        guest = request.env['mail.guest']._get_guest_from_request(request)
        if guest:
            return guest.sudo()._init_messaging()
        raise NotFound()

    @http.route('/mail/load_message_failures', methods=['POST'], type='json', auth='user')
    def mail_load_message_failures(self, **kwargs):
        return request.env.user.partner_id._message_fetch_failed()

    # --------------------------------------------------------------------------
    # Mailbox
    # --------------------------------------------------------------------------

    @http.route('/mail/inbox/messages', methods=['POST'], type='json', auth='user')
    def discuss_inbox_messages(self, max_id=None, min_id=None, limit=30, **kwargs):
        return request.env['mail.message']._message_fetch(domain=[('needaction', '=', True)], max_id=max_id, min_id=min_id, limit=limit).message_format()

    @http.route('/mail/history/messages', methods=['POST'], type='json', auth='user')
    def discuss_history_messages(self, max_id=None, min_id=None, limit=30, **kwargs):
        return request.env['mail.message']._message_fetch(domain=[('needaction', '=', False)], max_id=max_id, min_id=min_id, limit=limit).message_format()

    @http.route('/mail/starred/messages', methods=['POST'], type='json', auth='user')
    def discuss_starred_messages(self, max_id=None, min_id=None, limit=30, **kwargs):
        return request.env['mail.message']._message_fetch(domain=[('starred_partner_ids', 'in', [request.env.user.partner_id.id])], max_id=max_id, min_id=min_id, limit=limit).message_format()

    # --------------------------------------------------------------------------
    # Thread API (channel/chatter common)
    # --------------------------------------------------------------------------

    def _get_allowed_message_post_params(self):
        return {'attachment_ids', 'body', 'message_type', 'partner_ids', 'subtype_xmlid', 'parent_id'}

    @http.route('/mail/message/post', methods=['POST'], type='json', auth='public')
    def mail_message_post(self, thread_model, thread_id, post_data, **kwargs):
        if thread_model == 'mail.channel':
            channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(thread_id))
            thread = channel_member_sudo.channel_id
        else:
            thread = request.env[thread_model].browse(int(thread_id)).exists()
        return thread.message_post(**{key: value for key, value in post_data.items() if key in self._get_allowed_message_post_params()}).message_format()[0]

    @http.route('/mail/message/update_content', methods=['POST'], type='json', auth='public')
    def mail_message_update_content(self, message_id, body, attachment_ids):
        guest = request.env['mail.guest']._get_guest_from_request(request)
        message_sudo = guest.env['mail.message'].browse(message_id).sudo().exists()
        if not message_sudo.is_current_user_or_guest_author and not guest.env.user._is_admin():
            raise NotFound()
        message_sudo._update_content(body=body, attachment_ids=attachment_ids)
        return {
            'id': message_sudo.id,
            'body': message_sudo.body,
            'attachments': message_sudo.attachment_ids._attachment_format(),
        }

    @http.route('/mail/attachment/upload', methods=['POST'], type='http', auth='public')
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        channel_member = request.env['mail.channel.member']
        if thread_model == 'mail.channel':
            channel_member = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(thread_id))
        vals = {
            'name': ufile.filename,
            'raw': ufile.read(),
            'res_id': int(thread_id),
            'res_model': thread_model,
        }
        if is_pending and is_pending != 'false':
            # Add this point, the message related to the uploaded file does
            # not exist yet, so we use those placeholder values instead.
            vals.update({
                'res_id': 0,
                'res_model': 'mail.compose.message',
            })
        if channel_member.env.user.share:
            # Only generate the access token if absolutely necessary (= not for internal user).
            vals['access_token'] = channel_member.env['ir.attachment']._generate_access_token()
        try:
            attachment = channel_member.env['ir.attachment'].create(vals)
            attachment._post_add_create()
            attachmentData = {
                'filename': ufile.filename,
                'id': attachment.id,
                'mimetype': attachment.mimetype,
                'name': attachment.name,
                'size': attachment.file_size
            }
            if attachment.access_token:
                attachmentData['accessToken'] = attachment.access_token
        except AccessError:
            attachmentData = {'error': _("You are not allowed to upload an attachment here.")}
        return request.make_json_response(attachmentData)

    @http.route('/mail/attachment/delete', methods=['POST'], type='json', auth='public')
    def mail_attachment_delete(self, attachment_id, access_token=None, **kwargs):
        attachment_sudo = request.env['ir.attachment'].browse(int(attachment_id)).sudo().exists()
        if not attachment_sudo:
            target = request.env.user.partner_id
            request.env['bus.bus']._sendone(target, 'ir.attachment/delete', {'id': attachment_id})
            return
        if not request.env.user.share:
            # Check through standard access rights/rules for internal users.
            attachment_sudo.sudo(False)._delete_and_notify()
            return
        # For non-internal users 2 cases are supported:
        #   - Either the attachment is linked to a message: verify the request is made by the author of the message (portal user or guest).
        #   - Either a valid access token is given: also verify the message is pending (because unfortunately in portal a token is also provided to guest for viewing others' attachments).
        guest = request.env['mail.guest']._get_guest_from_request(request)
        message_sudo = guest.env['mail.message'].sudo().search([('attachment_ids', 'in', attachment_sudo.ids)], limit=1)
        if message_sudo:
            if not message_sudo.is_current_user_or_guest_author:
                raise NotFound()
        else:
            if not access_token or not attachment_sudo.access_token or not consteq(access_token, attachment_sudo.access_token):
                raise NotFound()
            if attachment_sudo.res_model != 'mail.compose.message' or attachment_sudo.res_id != 0:
                raise NotFound()
        attachment_sudo._delete_and_notify()

    @http.route('/mail/message/add_reaction', methods=['POST'], type='json', auth='public')
    def mail_message_add_reaction(self, message_id, content):
        guest_sudo = request.env['mail.guest']._get_guest_from_request(request).sudo()
        message_sudo = guest_sudo.env['mail.message'].browse(int(message_id)).exists()
        if not message_sudo:
            raise NotFound()
        if request.env.user.sudo()._is_public():
            if not guest_sudo or not message_sudo.model == 'mail.channel' or message_sudo.res_id not in guest_sudo.channel_ids.ids:
                raise NotFound()
            message_sudo._message_add_reaction(content=content)
            guests = [('insert', {'id': guest_sudo.id})]
            partners = []
        else:
            message_sudo.sudo(False)._message_add_reaction(content=content)
            guests = []
            partners = [('insert', {'id': request.env.user.partner_id.id})]
        reactions = message_sudo.env['mail.message.reaction'].search([('message_id', '=', message_sudo.id), ('content', '=', content)])
        return {
            'id': message_sudo.id,
            'messageReactionGroups': [('insert' if len(reactions) > 0 else 'insert-and-unlink', {
                'content': content,
                'count': len(reactions),
                'guests': guests,
                'message': {'id', message_sudo.id},
                'partners': partners,
            })],
        }

    @http.route('/mail/message/remove_reaction', methods=['POST'], type='json', auth='public')
    def mail_message_remove_reaction(self, message_id, content):
        guest_sudo = request.env['mail.guest']._get_guest_from_request(request).sudo()
        message_sudo = guest_sudo.env['mail.message'].browse(int(message_id)).exists()
        if not message_sudo:
            raise NotFound()
        if request.env.user.sudo()._is_public():
            if not guest_sudo or not message_sudo.model == 'mail.channel' or message_sudo.res_id not in guest_sudo.channel_ids.ids:
                raise NotFound()
            message_sudo._message_remove_reaction(content=content)
            guests = [('insert-and-unlink', {'id': guest_sudo.id})]
            partners = []
        else:
            message_sudo.sudo(False)._message_remove_reaction(content=content)
            guests = []
            partners = [('insert-and-unlink', {'id': request.env.user.partner_id.id})]
        reactions = message_sudo.env['mail.message.reaction'].search([('message_id', '=', message_sudo.id), ('content', '=', content)])
        return {
            'id': message_sudo.id,
            'messageReactionGroups': [('insert' if len(reactions) > 0 else 'insert-and-unlink', {
                'content': content,
                'count': len(reactions),
                'guests': guests,
                'message': {'id': message_sudo.id},
                'partners': partners,
            })],
        }

    # --------------------------------------------------------------------------
    # Channel API
    # --------------------------------------------------------------------------

    @http.route('/mail/channel/add_guest_as_member', methods=['POST'], type='json', auth='public')
    def mail_channel_add_guest_as_member(self, channel_id, channel_uuid, **kwargs):
        channel_sudo = request.env['mail.channel'].browse(int(channel_id)).sudo().exists()
        if not channel_sudo or not channel_sudo.uuid or not consteq(channel_sudo.uuid, channel_uuid):
            raise NotFound()
        if channel_sudo.channel_type == 'chat':
            raise NotFound()
        guest = channel_sudo.env['mail.guest']._get_guest_from_request(request)
        # Only guests should take this route.
        if not guest:
            raise NotFound()
        channel_member = channel_sudo.env['mail.channel.member']._get_as_sudo_from_request(request=request, channel_id=channel_id)
        # Do not add the guest to channel members if they are already member.
        if not channel_member:
            channel_sudo = channel_sudo.with_context(guest=guest)
            try:
                channel_sudo.add_members(guest_ids=[guest.id])
            except UserError:
                raise NotFound()

    @http.route('/mail/channel/messages', methods=['POST'], type='json', auth='public')
    def mail_channel_messages(self, channel_id, max_id=None, min_id=None, limit=30, **kwargs):
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        messages = channel_member_sudo.env['mail.message']._message_fetch(domain=[
            ('res_id', '=', channel_id),
            ('model', '=', 'mail.channel'),
            ('message_type', '!=', 'user_notification'),
        ], max_id=max_id, min_id=min_id, limit=limit)
        if not request.env.user._is_public():
            messages.set_message_done()
        return messages.message_format()

    @http.route('/mail/channel/set_last_seen_message', methods=['POST'], type='json', auth='public')
    def mail_channel_mark_as_seen(self, channel_id, last_message_id, **kwargs):
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        return channel_member_sudo.channel_id._channel_seen(int(last_message_id))

    @http.route('/mail/channel/ping', methods=['POST'], type='json', auth='public')
    def channel_ping(self, channel_id, rtc_session_id=None, check_rtc_session_ids=None):
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        if rtc_session_id:
            channel_member_sudo.channel_id.rtc_session_ids.filtered_domain([
                ('id', '=', int(rtc_session_id)),
                ('channel_member_id', '=', channel_member_sudo.id),
            ]).write({})  # update write_date
        current_rtc_sessions, outdated_rtc_sessions = channel_member_sudo._rtc_sync_sessions(check_rtc_session_ids=check_rtc_session_ids)
        return {'rtcSessions': [
            ('insert', [rtc_session_sudo._mail_rtc_session_format(complete_info=False) for rtc_session_sudo in current_rtc_sessions]),
            ('insert-and-unlink', [{'id': missing_rtc_session_sudo.id} for missing_rtc_session_sudo in outdated_rtc_sessions]),
        ]}

    # --------------------------------------------------------------------------
    # Chatter API
    # --------------------------------------------------------------------------

    @http.route('/mail/thread/data', methods=['POST'], type='json', auth='user')
    def mail_thread_data(self, thread_model, thread_id, request_list, **kwargs):
        thread = request.env[thread_model].with_context(active_test=False).search([('id', '=', thread_id)])
        return thread._get_mail_thread_data(request_list)

    @http.route('/mail/thread/messages', methods=['POST'], type='json', auth='user')
    def mail_thread_messages(self, thread_model, thread_id, max_id=None, min_id=None, limit=30, **kwargs):
        messages = request.env['mail.message']._message_fetch(domain=[
            ('res_id', '=', int(thread_id)),
            ('model', '=', thread_model),
            ('message_type', '!=', 'user_notification'),
        ], max_id=max_id, min_id=min_id, limit=limit)
        if not request.env.user._is_public():
            messages.set_message_done()
        return messages.message_format()

    @http.route('/mail/read_subscription_data', methods=['POST'], type='json', auth='user')
    def read_subscription_data(self, follower_id):
        """ Computes:
            - message_subtype_data: data about document subtypes: which are
                available, which are followed if any """
        request.env['mail.followers'].check_access_rights("read")
        follower = request.env['mail.followers'].sudo().browse(follower_id)
        follower.ensure_one()
        request.env[follower.res_model].check_access_rights("read")
        record = request.env[follower.res_model].browse(follower.res_id)
        record.check_access_rule("read")

        # find current model subtypes, add them to a dictionary
        subtypes = record._mail_get_message_subtypes()

        followed_subtypes_ids = set(follower.subtype_ids.ids)
        subtypes_list = [{
            'name': subtype.name,
            'res_model': subtype.res_model,
            'sequence': subtype.sequence,
            'default': subtype.default,
            'internal': subtype.internal,
            'followed': subtype.id in followed_subtypes_ids,
            'parent_model': subtype.parent_id.res_model,
            'id': subtype.id
        } for subtype in subtypes]
        return sorted(subtypes_list,
                      key=lambda it: (it['parent_model'] or '', it['res_model'] or '', it['internal'], it['sequence']))

    # --------------------------------------------------------------------------
    # RTC API TODO move check logic in routes.
    # --------------------------------------------------------------------------

    @http.route('/mail/rtc/session/notify_call_members', methods=['POST'], type="json", auth="public")
    def session_call_notify(self, peer_notifications):
        """ Sends content to other session of the same channel, only works if the user is the user of that session.
            This is used to send peer to peer information between sessions.

            :param peer_notifications: list of tuple with the following elements:
                - int sender_session_id: id of the session from which the content is sent
                - list target_session_ids: list of the ids of the sessions that should receive the content
                - string content: the content to send to the other sessions
        """
        guest = request.env['mail.guest']._get_guest_from_request(request)
        notifications_by_session = defaultdict(list)
        for sender_session_id, target_session_ids, content in peer_notifications:
            session_sudo = guest.env['mail.channel.rtc.session'].sudo().browse(int(sender_session_id)).exists()
            if not session_sudo or (session_sudo.guest_id and session_sudo.guest_id != guest) or (session_sudo.partner_id and session_sudo.partner_id != request.env.user.partner_id):
                continue
            notifications_by_session[session_sudo].append(([int(sid) for sid in target_session_ids], content))
        for session_sudo, notifications in notifications_by_session.items():
            session_sudo._notify_peers(notifications)

    @http.route('/mail/rtc/session/update_and_broadcast', methods=['POST'], type="json", auth="public")
    def session_update_and_broadcast(self, session_id, values):
        """ Update a RTC session and broadcasts the changes to the members of its channel,
            only works of the user is the user of that session.
            :param int session_id: id of the session to update
            :param dict values: write dict for the fields to update
        """
        if request.env.user._is_public():
            guest = request.env['mail.guest']._get_guest_from_request(request)
            if guest:
                session = guest.env['mail.channel.rtc.session'].sudo().browse(int(session_id)).exists()
                if session and session.guest_id == guest:
                    session._update_and_broadcast(values)
                    return
            return
        session = request.env['mail.channel.rtc.session'].sudo().browse(int(session_id)).exists()
        if session and session.partner_id == request.env.user.partner_id:
            session._update_and_broadcast(values)

    @http.route('/mail/rtc/channel/join_call', methods=['POST'], type="json", auth="public")
    def channel_call_join(self, channel_id, check_rtc_session_ids=None):
        """ Joins the RTC call of a channel if the user is a member of that channel
            :param int channel_id: id of the channel to join
        """
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        return channel_member_sudo._rtc_join_call(check_rtc_session_ids=check_rtc_session_ids)

    @http.route('/mail/rtc/channel/leave_call', methods=['POST'], type="json", auth="public")
    def channel_call_leave(self, channel_id):
        """ Disconnects the current user from a rtc call and clears any invitation sent to that user on this channel
            :param int channel_id: id of the channel from which to disconnect
        """
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        return channel_member_sudo._rtc_leave_call()

    @http.route('/mail/rtc/channel/cancel_call_invitation', methods=['POST'], type="json", auth="public")
    def channel_call_cancel_invitation(self, channel_id, member_ids=None):
        """ Sends invitations to join the RTC call to all connected members of the thread who are not already invited,
            if member_ids is provided, only the specified ids will be invited.

            :param list member_ids: list of member ids to invite
        """
        channel_member_sudo = request.env['mail.channel.member']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        return channel_member_sudo.channel_id._rtc_cancel_invitations(member_ids=member_ids)

    @http.route('/mail/rtc/audio_worklet_processor', methods=['GET'], type='http', auth='public')
    def audio_worklet_processor(self):
        """ Returns a JS file that declares a WorkletProcessor class in
            a WorkletGlobalScope, which means that it cannot be added to the
            bundles like other assets.
        """
        return request.make_response(
            file_open('mail/static/src/worklets/audio_processor.js', 'rb').read(),
            headers=[
                ('Content-Type', 'application/javascript'),
                ('Cache-Control', 'max-age=%s' % http.STATIC_CACHE),
            ]
        )

    # --------------------------------------------------------------------------
    # Guest API
    # --------------------------------------------------------------------------

    @http.route('/mail/guest/update_name', methods=['POST'], type='json', auth='public')
    def mail_guest_update_name(self, guest_id, name):
        guest = request.env['mail.guest']._get_guest_from_request(request)
        guest_to_rename_sudo = guest.env['mail.guest'].browse(guest_id).sudo().exists()
        if not guest_to_rename_sudo:
            raise NotFound()
        if guest_to_rename_sudo != guest and not request.env.user._is_admin():
            raise NotFound()
        guest_to_rename_sudo._update_name(name)
