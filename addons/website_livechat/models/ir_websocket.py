# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models

THEME_SYNC_CHANNEL_PATTERN = re.compile(r"im_livechat\.channel_(\d+)/theme_sync")


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels):
        new_channels = []
        for channel in channels:
            match = isinstance(channel, str) and THEME_SYNC_CHANNEL_PATTERN.fullmatch(channel)
            if not match:
                new_channels.append(channel)
                continue
            record = self.env["im_livechat.channel"].browse(int(match[1]))
            if record.exists() and record.has_access("read"):
                new_channels.append((record, "THEME_SYNC"))
        return super()._build_bus_channel_list(new_channels)
