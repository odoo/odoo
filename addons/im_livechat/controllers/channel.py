# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from werkzeug.exceptions import BadRequest, NotFound

from odoo import Command
from odoo.http import request, route
from odoo.addons.mail.controllers.discuss.channel import ChannelController


class LivechatChannelController(ChannelController):
    @route("/im_livechat/session/update_note", auth="user", methods=["POST"], type="jsonrpc")
    def livechat_session_update_note(self, channel_id, note):
        """Internal users having the rights to read the session can update its note."""
        if self.env.user.share:
            raise NotFound()
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        # sudo: discuss.channel - internal users having the rights to read the session can update its note
        # Markup: note sanitized when written on the field
        channel.sudo().livechat_note = Markup(note)

    @route("/im_livechat/session/update_status", auth="user", methods=["POST"], type="jsonrpc")
    def livechat_session_update_status(self, channel_id, livechat_status):
        """Internal users having the rights to read the session can update its status."""
        if self.env.user.share:
            raise NotFound()
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        # sudo: discuss.channel - internal users having the rights to read the session can update its status
        channel.sudo().livechat_status = livechat_status

    @route("/im_livechat/conversation/update_tags", auth="user", methods=["POST"], type="jsonrpc")
    def livechat_conversation_update_tags(self, channel_id, tag_ids, method="ADD"):
        """Add or remove tags from a live chat conversation."""
        if not self.env["im_livechat.conversation.tag"].has_access("write"):
            raise NotFound()
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        # sudo: discuss.channel - internal users having the rights to read the conversation and to
        # write tags can update the tags
        if method == "ADD":
            channel.sudo().livechat_conversation_tag_ids = [
                Command.link(tag_id) for tag_id in tag_ids
            ]
        elif method == "DELETE":
            channel.sudo().livechat_conversation_tag_ids = [
                Command.unlink(tag_id) for tag_id in tag_ids
            ]
        if channel.livechat_status == "need_help":
            request.env.ref("im_livechat.im_livechat_group_user")._bus_send(
                "im_livechat.looking_for_help/tags",
                {
                    "channel_id": channel.id,
                    "tag_ids": channel.sudo().livechat_conversation_tag_ids.ids,
                },
                subchannel="LOOKING_FOR_HELP",
            )

    @route(
        "/im_livechat/conversation/write_expertises", auth="user", methods=["POST"], type="jsonrpc"
    )
    def livechat_conversation_write_expertises(self, channel_id, orm_commands):
        if any(cmd[0] not in (Command.LINK, Command.UNLINK) for cmd in orm_commands):
            raise BadRequest(
                self.env._("Write expertises: Only LINK and UNLINK commands are allowed.")
            )
        if not self.env.user.has_group("im_livechat.im_livechat_group_user"):
            return
        if channel := request.env["discuss.channel"].search(
            [("id", "=", channel_id), ("channel_type", "=", "livechat")]
        ):
            # sudo: discuss.channel - live chat users can update the expertises of any live chat.
            channel.sudo().livechat_expertise_ids = orm_commands

    @route(
        "/im_livechat/conversation/create_and_link_expertise",
        auth="user",
        methods=["POST"],
        type="jsonrpc",
    )
    def livechat_conversation_create_and_link_expertise(self, channel_id, expertise_name):
        channel = request.env["discuss.channel"].search(
            [("id", "=", channel_id), ("channel_type", "=", "livechat")]
        )
        if not channel:
            return
        stripped_name = expertise_name.strip()
        expertise = request.env["im_livechat.expertise"].search([("name", "=", stripped_name)])
        if not expertise:
            expertise = request.env["im_livechat.expertise"].create({"name": stripped_name})
        channel.livechat_expertise_ids = [Command.link(expertise.id)]
