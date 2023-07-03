# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq


class ChannelController(http.Controller):
    @http.route("/discuss/channel/members", methods=["POST"], type="json", auth="public")
    def discuss_channel_members(self, channel_id, known_member_ids):
        channel_member = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=channel_id
        )
        return channel_member.channel_id.sudo().load_more_members(known_member_ids)

    @http.route("/discuss/channel/add_guest_as_member", methods=["POST"], type="json", auth="public")
    def discuss_channel_add_guest_as_member(self, channel_id, channel_uuid):
        channel_sudo = request.env["discuss.channel"].browse(int(channel_id)).sudo().exists()
        if not channel_sudo or not channel_sudo.uuid or not consteq(channel_sudo.uuid, channel_uuid):
            raise NotFound()
        if channel_sudo.channel_type == "chat":
            raise NotFound()
        guest = channel_sudo.env["mail.guest"]._get_guest_from_request(request)
        # Only guests should take this route.
        if not guest:
            raise NotFound()
        channel_member = channel_sudo.env["discuss.channel.member"]._get_as_sudo_from_request(
            request=request, channel_id=channel_id
        )
        # Do not add the guest to channel members if they are already member.
        if not channel_member:
            channel_sudo = channel_sudo.with_context(guest=guest)
            try:
                channel_sudo.add_members(guest_ids=[guest.id])
            except UserError:
                raise NotFound()

    @http.route("/discuss/channel/update_avatar", methods=["POST"], type="json")
    def discuss_channel_avatar_update(self, channel_id, data):
        channel = request.env["discuss.channel"].browse(int(channel_id)).exists()
        if not channel or not data:
            raise NotFound()
        channel.write({"image_128": data})

    @http.route("/discuss/channel/info", methods=["POST"], type="json")
    def discuss_channel_info(self, channel_id):
        member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
        return member_sudo.channel_id._channel_info()

    @http.route("/discuss/channel/messages", methods=["POST"], type="json", auth="public")
    def discuss_channel_messages(self, channel_id, before=None, after=None, limit=30, around=None):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
        domain = [
            ("res_id", "=", channel_id),
            ("model", "=", "discuss.channel"),
            ("message_type", "!=", "user_notification"),
        ]
        messages = channel_member_sudo.env["mail.message"]._message_fetch(domain, before, after, around, limit)
        if not request.env.user._is_public() and not around:
            messages.set_message_done()
        return messages.message_format()

    @http.route("/discuss/channel/pinned_messages", methods=["POST"], type="json", auth="public")
    def discuss_channel_pins(self, channel_id):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
        return channel_member_sudo.channel_id.pinned_message_ids.sorted(key="pinned_at", reverse=True).message_format()

    @http.route("/discuss/channel/set_last_seen_message", methods=["POST"], type="json", auth="public")
    def discuss_channel_mark_as_seen(self, channel_id, last_message_id, allow_older=False):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
        return channel_member_sudo.channel_id._channel_seen(last_message_id, allow_older=allow_older)

    @http.route("/discuss/channel/notify_typing", methods=["POST"], type="json", auth="public")
    def discuss_channel_notify_typing(self, channel_id, is_typing):
        channel_member_sudo = request.env["discuss.channel.member"]._get_as_sudo_from_request_or_raise(
            request=request, channel_id=int(channel_id)
        )
        channel_member_sudo._notify_typing(is_typing)
