# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from werkzeug.exceptions import NotFound

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
