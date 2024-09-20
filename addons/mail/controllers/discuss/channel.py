# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store


class DiscussChannelWebclientController(WebclientController):
    """Override to add discuss channel specific features."""
    def _process_request_for_all(self, store, **kwargs):
        """Override to return channel as member and last messages."""
        super()._process_request_for_all(store, **kwargs)
        if kwargs.get("channels_as_member"):
            channels = request.env["discuss.channel"]._get_channels_as_member()
            # fetch channels data before messages to benefit from prefetching (channel info might
            # prefetch a lot of data that message format could use)
            store.add(channels)
            store.add(channels._get_last_messages(), for_current_user=True)


class ChannelController(http.Controller):
    @http.route("/discuss/channel/members", methods=["POST"], type="json", auth="public", readonly=True)
    @add_guest_to_context
    def discuss_channel_members(self, channel_id, known_member_ids):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return channel._load_more_members(known_member_ids)

    @http.route("/discuss/channel/update_avatar", methods=["POST"], type="json")
    def discuss_channel_avatar_update(self, channel_id, data):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel or not data:
            raise NotFound()
        channel.write({"image_128": data})

    @http.route("/discuss/channel/info", methods=["POST"], type="json", auth="public", readonly=True)
    @add_guest_to_context
    def discuss_channel_info(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            return
        return Store(channel).get_result()

    @http.route("/discuss/channel/messages", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_messages(self, channel_id, search_term=None, before=None, after=None, limit=30, around=None):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        domain = [
            ("res_id", "=", channel_id),
            ("model", "=", "discuss.channel"),
            ("message_type", "!=", "user_notification"),
        ]
        res = request.env["mail.message"]._message_fetch(
            domain, search_term=search_term, before=before, after=after, around=around, limit=limit
        )
        messages = res.pop("messages")
        if not request.env.user._is_public() and not around:
            messages.set_message_done()
        return {
            **res,
            "data": Store(messages, for_current_user=True).get_result(),
            "messages": Store.many_ids(messages),
        }

    @http.route("/discuss/channel/pinned_messages", methods=["POST"], type="json", auth="public", readonly=True)
    @add_guest_to_context
    def discuss_channel_pins(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        messages = channel.pinned_message_ids.sorted(key="pinned_at", reverse=True)
        return Store(messages, for_current_user=True).get_result()

    @http.route("/discuss/channel/mark_as_read", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_mark_as_read(self, channel_id, last_message_id, sync=False):
        member = request.env["discuss.channel.member"].search([
            ("channel_id", "=", channel_id),
            ("is_self", "=", True),
        ])
        if not member:
            return  # ignore if the member left in the meantime
        member._mark_as_read(last_message_id, sync=sync)

    @http.route("/discuss/channel/mark_as_unread", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_mark_as_unread(self, channel_id, message_id):
        member = request.env["discuss.channel.member"].search([
            ("channel_id", "=", channel_id),
            ("is_self", "=", True),
        ])
        if not member:
            raise NotFound()
        return member._set_new_message_separator(message_id, sync=True)

    @http.route("/discuss/channel/notify_typing", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_notify_typing(self, channel_id, is_typing):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise request.not_found()
        member = channel._find_or_create_member_for_self()
        if not member:
            raise NotFound()
        member._notify_typing(is_typing)

    @http.route("/discuss/channel/attachments", methods=["POST"], type="json", auth="public", readonly=True)
    @add_guest_to_context
    def load_attachments(self, channel_id, limit=30, before=None):
        """Load attachments of a channel. If before is set, load attachments
        older than the given id.
        :param channel_id: id of the channel
        :param limit: maximum number of attachments to return
        :param before: id of the attachment from which to load older attachments
        """
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        domain = [
            ["res_id", "=", channel_id],
            ["res_model", "=", "discuss.channel"],
        ]
        if before:
            domain.append(["id", "<", before])
        # sudo: ir.attachment - reading attachments of a channel that the current user can access
        return Store(
            request.env["ir.attachment"].sudo().search(domain, limit=limit, order="id DESC")
        ).get_result()

    @http.route("/discuss/channel/fold", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_fold(self, channel_id, state, state_count):
        member = request.env["discuss.channel.member"].search([("channel_id", "=", channel_id), ("is_self", "=", True)])
        if not member:
            raise NotFound()
        return member._channel_fold(state, state_count)

    @http.route("/discuss/channel/join", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_join(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        channel._find_or_create_member_for_self()
        return Store(channel).get_result()

    @http.route("/discuss/channel/sub_channel/create", methods=["POST"], type="json", auth="public")
    def discuss_channel_sub_channel_create(self, parent_channel_id, from_message_id=None, name=None):
        channel = request.env["discuss.channel"].search([("id", "=", parent_channel_id)])
        if not channel:
            raise NotFound()
        sub_channel = channel._create_sub_channel(from_message_id, name)
        return {
            "data": Store(sub_channel).add(sub_channel).get_result(),
            "sub_channel": Store.one_id(sub_channel),
        }

    @http.route("/discuss/channel/sub_channel/fetch", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_sub_channel_fetch(self, parent_channel_id, search_term=None, before=None, limit=30):
        channel = request.env["discuss.channel"].search([("id", "=", parent_channel_id)])
        if not channel:
            raise NotFound()
        domain = [("parent_channel_id", "=", channel.id)]
        if before:
            domain.append(("id", "<", before))
        if search_term:
            domain.append(("name", "ilike", search_term))
        sub_channels = request.env["discuss.channel"].search(domain, order="id desc", limit=limit)
        return Store(sub_channels).add(sub_channels._get_last_messages()).get_result()
