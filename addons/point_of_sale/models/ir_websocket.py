# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import models

# Channel requested by the PoS (`pos.config_webrtc_<id>`), replaced by `(config, "webrtc")` if allowed.
WEBRTC_CHANNEL_PREFIX = "pos.config_webrtc_"
WEBRTC_CHANNEL_REGEX = re.compile(rf"^{re.escape(WEBRTC_CHANNEL_PREFIX)}(\d+)$")


class IrWebsocket(models.AbstractModel):
    _inherit = 'ir.websocket'

    def _build_bus_channel_list(self, channels):
        # The signaling messages contain the network addresses of the devices,
        # which are private data: `pos.config_webrtc_<id>` is only accepted if
        # the user can read the config.
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
