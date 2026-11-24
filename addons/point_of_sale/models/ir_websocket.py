# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import models

# Asked by a PoS terminal to receive the WebRTC signaling of its config.
WEBRTC_CHANNEL_PREFIX = "pos.config_webrtc_"
WEBRTC_CHANNEL_REGEX = re.compile(rf"^{re.escape(WEBRTC_CHANNEL_PREFIX)}(\d+)$")


class IrWebsocket(models.AbstractModel):
    _inherit = 'ir.websocket'

    def _build_bus_channel_list(self, channels):
        # The signaling messages contain the network addresses of the terminals:
        # unlike the access token channel of the config, known by the customer
        # display and the self order, this channel is only given to the users
        # who can read the config.
        config_ids = set()
        other_channels = []
        for channel in channels:
            if isinstance(channel, str) and channel.startswith(WEBRTC_CHANNEL_PREFIX):
                if match := WEBRTC_CHANNEL_REGEX.match(channel):
                    config_ids.add(int(match[1]))
            else:
                other_channels.append(channel)
        configs = self.env['pos.config'].browse(list(config_ids)).exists()._filtered_access('read')
        return super()._build_bus_channel_list(other_channels + [(config, "webrtc") for config in configs])
