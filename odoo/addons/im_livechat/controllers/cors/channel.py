# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers.discuss.channel import ChannelController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class LivechatChannelController(ChannelController):
    @route("/im_livechat/cors/channel/messages", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_channel_messages(self, guest_token, channel_id, before=None, after=None, limit=30, around=None):
        force_guest_env(guest_token)
        return self.discuss_channel_messages(channel_id, before, after, limit, around)

    @route("/im_livechat/cors/channel/set_last_seen_message", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_channel_mark_as_seen(self, guest_token, channel_id, last_message_id, allow_older=False):
        force_guest_env(guest_token)
        return self.discuss_channel_mark_as_seen(channel_id, last_message_id, allow_older)
