# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from werkzeug.exceptions import NotFound

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
