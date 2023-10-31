# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from werkzeug.exceptions import NotFound

from odoo import fields, http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class ChannelController(http.Controller):
    @http.route("/discuss/channel/members", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_members(self, channel_id, known_member_ids):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return channel.load_more_members(known_member_ids)

    @http.route("/discuss/channel/update_avatar", methods=["POST"], type="json")
    def discuss_channel_avatar_update(self, channel_id, data):
        channel = request.env["discuss.channel"].browse(int(channel_id)).exists()
        if not channel or not data:
            raise NotFound()
        channel.write({"image_128": data})

    @http.route("/discuss/channel/info", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_info(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            return
        return channel._channel_info()[0]

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
        if not request.env.user._is_public() and not around:
            res["messages"].set_message_done()
        return {**res, "messages": res["messages"].message_format()}

    @http.route("/discuss/channel/pinned_messages", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_pins(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return channel.pinned_message_ids.sorted(key="pinned_at", reverse=True).message_format()

    @http.route("/discuss/channel/mute", methods=["POST"], type="json", auth="user")
    def discuss_channel_mute(self, channel_id, minutes):
        """Mute notifications for the given number of minutes.
        :param minutes: (integer) number of minutes to mute notifications, -1 means mute until the user unmutes
        """
        member = request.env["discuss.channel.member"].search([("channel_id", "=", channel_id), ("is_self", "=", True)])
        if not member:
            raise request.not_found()
        if minutes == -1:
            member.mute_until_dt = datetime.max
        elif minutes:
            member.mute_until_dt = fields.Datetime.now() + relativedelta(minutes=minutes)
            request.env.ref("mail.ir_cron_discuss_channel_member_unmute")._trigger(member.mute_until_dt)
        else:
            member.mute_until_dt = False
        channel_data = {
            "id": member.channel_id.id,
            "model": "discuss.channel",
            "mute_until_dt": member.mute_until_dt,
        }
        request.env["bus.bus"]._sendone(member.partner_id, "mail.record/insert", {"Thread": channel_data})

    @http.route("/discuss/channel/update_custom_notifications", methods=["POST"], type="json", auth="user")
    def discuss_channel_update_custom_notifications(self, channel_id, custom_notifications):
        member = request.env["discuss.channel.member"].search([("channel_id", "=", channel_id), ("is_self", "=", True)])
        if not member:
            raise request.not_found()
        member.custom_notifications = custom_notifications
        channel_data = {
            "custom_notifications": member.custom_notifications,
            "id": member.channel_id.id,
            "model": "discuss.channel",
        }
        request.env["bus.bus"]._sendone(member.partner_id, "mail.record/insert", {"Thread": channel_data})

    @http.route("/discuss/channel/set_last_seen_message", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_mark_as_seen(self, channel_id, last_message_id, allow_older=False):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        return channel._channel_seen(last_message_id, allow_older=allow_older)

    @http.route("/discuss/channel/notify_typing", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def discuss_channel_notify_typing(self, channel_id, is_typing):
        member = request.env["discuss.channel.member"].search([("channel_id", "=", channel_id), ("is_self", "=", True)])
        if not member:
            raise NotFound()
        member._notify_typing(is_typing)

    @http.route("/discuss/channel/attachments", methods=["POST"], type="json", auth="public")
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
        return request.env["ir.attachment"].sudo().search(domain, limit=limit, order="id DESC")._attachment_format()
