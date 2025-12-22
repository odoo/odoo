# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers.discuss.channel import ChannelController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class LivechatChannelController(ChannelController):
    @route("/im_livechat/cors/channel/messages", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_channel_messages(self, guest_token, channel_id, before=None, after=None, limit=30, around=None):
        force_guest_env(guest_token)
        return self.discuss_channel_messages(channel_id, before, after, limit, around)

    @route("/im_livechat/cors/channel/mark_as_read", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_channel_mark_as_read(self, guest_token, **kwargs):
        force_guest_env(guest_token)
        return self.discuss_channel_mark_as_read(**kwargs)

    @route("/im_livechat/cors/channel/fold", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_channel_fold(self, guest_token, channel_id, state, state_count):
        force_guest_env(guest_token)
        return self.discuss_channel_fold(channel_id, state, state_count)

    @route("/im_livechat/cors/channel/notify_typing", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_channel_notify_typing(self, guest_token, channel_id, is_typing):
        force_guest_env(guest_token)
        return self.discuss_channel_notify_typing(channel_id, is_typing)
