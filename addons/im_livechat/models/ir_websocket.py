# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels):
        channels = list(channels)  # do not alter original list
        if any(
            channel == "im_livechat.looking_for_help"
            for channel in channels
            if isinstance(channel, str)
        ):
            if self.env.user.has_group("im_livechat.im_livechat_group_user"):
                channels.append(
                    (self.env.ref("im_livechat.im_livechat_group_user"), "LOOKING_FOR_HELP")
                )
            channels.remove("im_livechat.looking_for_help")
        return super()._build_bus_channel_list(channels)
