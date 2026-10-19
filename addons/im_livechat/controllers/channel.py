# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from werkzeug.exceptions import BadRequest, NotFound

from odoo.fields import Command
from odoo.http import request

from odoo.addons.mail.controllers.discuss.channel import ChannelController
from odoo.addons.mail.tools.discuss import mail_route


class LivechatChannelController(ChannelController):
    @mail_route("/im_livechat/session/update_note", auth="user", methods=["POST"], type="jsonrpc")
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

    @mail_route("/im_livechat/session/update_status", auth="user", methods=["POST"], type="jsonrpc")
    def livechat_session_update_status(self, channel_id, livechat_status):
        """Internal users having the rights to read the session can update its status."""
        if self.env.user.share:
            raise NotFound()
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        # sudo: discuss.channel - internal users having the rights to read the session can update its status
        channel.sudo().livechat_status = livechat_status

    @mail_route(
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

    @mail_route(
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
