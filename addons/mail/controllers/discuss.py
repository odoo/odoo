# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request
from odoo.tools import consteq
from odoo.tools.misc import get_lang
from odoo.tools.translate import _
from werkzeug.exceptions import NotFound


class DiscussController(http.Controller):

    # --------------------------------------------------------------------------
    # Public Pages
    # --------------------------------------------------------------------------

    @http.route('/chat/<int:channel_id>/<string:invitation_token>', methods=['GET'], type='http', auth='public')
    def discuss_channel_invitation(self, channel_id, invitation_token, **kwargs):
        channel_sudo = request.env['mail.channel'].browse(int(channel_id)).sudo().exists()
        if not channel_sudo or not channel_sudo.uuid or not consteq(channel_sudo.uuid, invitation_token):
            raise NotFound()
        response = request.redirect(f'/discuss/channel/{channel_sudo.id}')
        if request.env['mail.channel.partner']._get_as_sudo_from_request(request=request, channel_id=int(channel_id)):
            return response
        if channel_sudo.channel_type == 'chat':
            raise NotFound()
        if request.session.uid:
            channel_sudo.add_members([request.env.user.partner_id.id])
            return response
        guest = request.env['mail.guest']._get_guest_from_request(request)
        if not guest:
            guest = request.env['mail.guest'].sudo().create({
                'country_id': request.env['res.country'].sudo().search([('code', '=', request.session.get('geoip', {}).get('country_code'))], limit=1).id,
                'lang': get_lang(request.env).code,
                'name': _("Guest"),
                'timezone': request.env['mail.guest']._get_timezone_from_request(request),
            })
            # Discuss Guest ID: every route in this file will make use of it to authenticate
            # the guest through `_get_as_sudo_from_request` or `_get_as_sudo_from_request_or_raise`.
            expiration_date = datetime.now() + timedelta(days=365)
            response.set_cookie(guest._cookie_name, f"{guest.id}{guest._cookie_separator}{guest.access_token}", httponly=True, expires=expiration_date)
        channel_sudo.add_members(guest_ids=[guest.id])
        return response

    @http.route('/discuss/channel/<int:channel_id>', methods=['GET'], type='http', auth='public')
    def discuss_channel(self, channel_id, **kwargs):
        channel_partner_sudo = request.env['mail.channel.partner']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        return request.render('mail.discuss_public_channel_template', {
            'channel_sudo': channel_partner_sudo.channel_id,
            'session_info': channel_partner_sudo.env['ir.http'].session_info(),
        })

    # --------------------------------------------------------------------------
    # Semi-Static Content (GET requests with possible cache)
    # --------------------------------------------------------------------------

    @http.route('/mail/channel/<int:channel_id>/partner/<int:partner_id>/avatar_128', methods=['GET'], type='http', auth='public')
    def mail_channel_partner_avatar_128(self, channel_id, partner_id, **kwargs):
        channel_partner_sudo = request.env['mail.channel.partner']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        if not channel_partner_sudo.env['mail.channel.partner'].search([('channel_id', '=', int(channel_id)), ('partner_id', '=', int(partner_id))], limit=1):
            raise NotFound()
        return channel_partner_sudo.env['ir.http']._content_image(model='res.partner', res_id=int(partner_id), field='avatar_128')

    @http.route('/mail/channel/<int:channel_id>/guest/<int:guest_id>/avatar_128', methods=['GET'], type='http', auth='public')
    def mail_channel_guest_avatar_128(self, channel_id, guest_id, **kwargs):
        channel_partner_sudo = request.env['mail.channel.partner']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        if not channel_partner_sudo.env['mail.channel.partner'].search([('channel_id', '=', int(channel_id)), ('guest_id', '=', int(guest_id))], limit=1):
            raise NotFound()
        return channel_partner_sudo.env['ir.http']._content_image(model='mail.guest', res_id=int(guest_id), field='avatar_128')

    @http.route('/mail/channel/<int:channel_id>/attachment/<int:attachment_id>', methods=['GET'], type='http', auth='public')
    def mail_channel_attachment(self, channel_id, attachment_id, **kwargs):
        channel_partner_sudo = request.env['mail.channel.partner']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        if not channel_partner_sudo.env['ir.attachment'].search([('id', '=', int(attachment_id)), ('res_id', '=', int(channel_id)), ('res_model', '=', 'mail.channel')], limit=1):
            raise NotFound()
        return channel_partner_sudo.env['ir.http']._get_content_common(res_id=int(attachment_id), download=True)

    @http.route('/mail/channel/<int:channel_id>/image/<int:attachment_id>/<int:width>x<int:height>', methods=['GET'], type='http', auth='public')
    def fetch_image(self, channel_id, attachment_id, width, height, **kwargs):
        channel_partner_sudo = request.env['mail.channel.partner']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        if not channel_partner_sudo.env['ir.attachment'].search([('id', '=', int(attachment_id)), ('res_id', '=', int(channel_id)), ('res_model', '=', 'mail.channel')], limit=1):
            raise NotFound()
        return channel_partner_sudo.env['ir.http']._content_image(res_id=int(attachment_id), height=int(height), width=int(width))

    # --------------------------------------------------------------------------
    # Client Initialization
    # --------------------------------------------------------------------------

    @http.route('/mail/init_messaging', methods=['POST'], type='json', auth='public')
    def mail_init_messaging(self, **kwargs):
        if request.session.uid:
            return request.env.user._init_messaging()
        guest = request.env['mail.guest']._get_guest_from_request(request)
        if guest:
            return guest.sudo()._init_messaging()
        raise NotFound()

    # --------------------------------------------------------------------------
    # Mailbox
    # --------------------------------------------------------------------------

    @http.route('/mail/inbox/messages', methods=['POST'], type='json', auth='user')
    def discuss_inbox_messages(self, max_id=None, min_id=None, limit=30, **kwargs):
        return request.env['mail.message']._message_fetch(domain=[('needaction', '=', True)], max_id=max_id, min_id=min_id, limit=limit)

    @http.route('/mail/history/messages', methods=['POST'], type='json', auth='user')
    def discuss_history_messages(self, max_id=None, min_id=None, limit=30, **kwargs):
        return request.env['mail.message']._message_fetch(domain=[('needaction', '=', False)], max_id=max_id, min_id=min_id, limit=limit)

    @http.route('/mail/starred/messages', methods=['POST'], type='json', auth='user')
    def discuss_starred_messages(self, max_id=None, min_id=None, limit=30, **kwargs):
        return request.env['mail.message']._message_fetch(domain=[('starred_partner_ids', 'in', [request.env.user.partner_id.id])], max_id=max_id, min_id=min_id, limit=limit)

    # --------------------------------------------------------------------------
    # Thread API (channel/chatter common)
    # --------------------------------------------------------------------------

    @http.route('/mail/message/post', methods=['POST'], type='json', auth='public')
    def mail_message_post(self, thread_model, thread_id, post_data, **kwargs):
        if thread_model == 'mail.channel':
            channel_partner_sudo = request.env['mail.channel.partner']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(thread_id))
            thread = channel_partner_sudo.channel_id
        else:
            thread = request.env[thread_model].browse(int(thread_id)).exists()
        allowed_params = {'attachment_ids', 'body', 'message_type', 'partner_ids', 'subtype_xmlid'}
        return thread.message_post(**{key: value for key, value in post_data.items() if key in allowed_params}).message_format()[0]

    @http.route('/mail/message/update_content', methods=['POST'], type='json', auth='public')
    def mail_message_update_content(self, message_id, body):
        guest = request.env['mail.guest']._get_guest_from_request(request)
        message_sudo = guest.env['mail.message'].browse(message_id).sudo().exists()
        if not message_sudo.is_current_user_or_guest_author and not guest.env.user.has_group('base.group_system'):
            raise NotFound()
        message_sudo._update_content(body=body)
        return {
            'id': message_sudo.id,
            'body': message_sudo.body,
        }

    @http.route('/mail/attachment/upload', methods=['POST'], type='http', auth='public')
    def mail_attachment_upload(self, ufile, thread_id, thread_model, is_pending=False, **kwargs):
        channel_partner = request.env['mail.channel.partner']
        if thread_model == 'mail.channel':
            channel_partner = request.env['mail.channel.partner']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(thread_id))
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
        if channel_partner.env.user.share:
            # Only generate the access token if absolutely necessary (= not for internal user).
            vals['access_token'] = channel_partner.env['ir.attachment']._generate_access_token()
        attachment = channel_partner.env['ir.attachment'].create(vals)
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
        return request.make_response(
            data=json.dumps(attachmentData),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/mail/attachment/delete', methods=['POST'], type='json', auth='public')
    def mail_attachment_delete(self, attachment_id, access_token=None, **kwargs):
        attachment_sudo = request.env['ir.attachment'].browse(int(attachment_id)).sudo().exists()
        if not attachment_sudo:
            raise NotFound()
        if not request.env.user.share:
            # Check through standard access rights/rules for internal users.
            return attachment_sudo.sudo(False).unlink()
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
        return attachment_sudo.unlink()

    # --------------------------------------------------------------------------
    # Channel API
    # --------------------------------------------------------------------------

    @http.route('/mail/channel/messages', methods=['POST'], type='json', auth='public')
    def mail_channel_messages(self, channel_id, max_id=None, min_id=None, limit=30, **kwargs):
        channel_partner_sudo = request.env['mail.channel.partner']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        return channel_partner_sudo.env['mail.message']._message_fetch(domain=[
            ('res_id', '=', channel_id),
            ('model', '=', 'mail.channel'),
            ('message_type', '!=', 'user_notification'),
        ], max_id=max_id, min_id=min_id, limit=limit)

    @http.route('/mail/channel/set_last_seen_message', methods=['POST'], type='json', auth='public')
    def mail_channel_mark_as_seen(self, channel_id, last_message_id, **kwargs):
        channel_partner_sudo = request.env['mail.channel.partner']._get_as_sudo_from_request_or_raise(request=request, channel_id=int(channel_id))
        return channel_partner_sudo.channel_id._channel_seen(int(last_message_id))

    # --------------------------------------------------------------------------
    # Chatter API
    # --------------------------------------------------------------------------

    @http.route('/mail/thread/messages', methods=['POST'], type='json', auth='user')
    def mail_thread_messages(self, thread_model, thread_id, max_id=None, min_id=None, limit=30, **kwargs):
        return request.env['mail.message']._message_fetch(domain=[
            ('res_id', '=', int(thread_id)),
            ('model', '=', thread_model),
            ('message_type', '!=', 'user_notification'),
        ], max_id=max_id, min_id=min_id, limit=limit)

    @http.route('/mail/read_followers', methods=['POST'], type='json', auth='user')
    def read_followers(self, res_model, res_id):
        request.env['mail.followers'].check_access_rights("read")
        request.env[res_model].check_access_rights("read")
        request.env[res_model].browse(res_id).check_access_rule("read")
        follower_recs = request.env['mail.followers'].search([('res_model', '=', res_model), ('res_id', '=', res_id)])

        followers = []
        follower_id = None
        for follower in follower_recs:
            if follower.partner_id == request.env.user.partner_id:
                follower_id = follower.id
            followers.append({
                'id': follower.id,
                'partner_id': follower.partner_id.id,
                'name': follower.name,
                'display_name': follower.display_name,
                'email': follower.email,
                'is_active': follower.is_active,
                # When editing the followers, the "pencil" icon that leads to the edition of subtypes
                # should be always be displayed and not only when "debug" mode is activated.
                'is_editable': True
            })
        return {
            'followers': followers,
            'subtypes': self.read_subscription_data(follower_id) if follower_id else None
        }

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

    @http.route('/mail/get_suggested_recipients', methods=['POST'], type='json', auth='user')
    def message_get_suggested_recipients(self, model, res_ids):
        records = request.env[model].browse(res_ids)
        try:
            records.check_access_rule('read')
            records.check_access_rights('read')
        except Exception:
            return {}
        return records._message_get_suggested_recipients()
