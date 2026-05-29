# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.mail.controllers.discuss.channel import ChannelController


class LivechatChannelController(ChannelController):
    @route(
        "/im_livechat/cors/channel/mark_as_read",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_channel_mark_as_read(self, guest_token, **kwargs):
        return self.discuss_channel_mark_as_read(**kwargs)

    @route(
        "/im_livechat/cors/channel/notify_typing",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_channel_notify_typing(self, guest_token, channel_id, is_typing):
        return self.discuss_channel_notify_typing(channel_id, is_typing)
