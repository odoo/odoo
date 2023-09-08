# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers.discuss.channel import ChannelController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class LivechatChannelController(ChannelController):
    @route("/discuss/channel/messages", cors="*")
    @add_guest_to_context
    def discuss_channel_messages(self, channel_id, before=None, after=None, limit=30, around=None):
        return super().discuss_channel_messages(channel_id, before, after, limit, around)
