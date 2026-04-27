# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels):
        if self.env.uid:
            channels = self._add_spreadsheet_collaborative_bus_channels(channels)
        return super()._build_bus_channel_list(channels)

    def _add_spreadsheet_collaborative_bus_channels(self, channels):
        """Add collaborative bus channels for active spreadsheets.

        Listening to channel "spreadsheet_collaborative_session:{res_model}:{res_id}"
        or "spreadsheet_collaborative_session:{res_model}:{res_id}:{access_token}"
        tells the server the spreadsheet is active. But only users with read access
        can actually read the associate bus messages.
        We manually add the channel if the user has read access.
        This channel is used to safely send messages to allowed users.

        :param channels: bus channels
        :return: channels
        """
        channels = list(channels)
        for channel in channels:
            if not isinstance(channel, str):
                continue
            if channel.startswith("spreadsheet_collaborative_session:"):
                record = self._check_spreadsheet_channel(channel)
                if record:
                    channels.append(record)
        return channels

    def _check_spreadsheet_channel(self, channel):
        params = channel.split(":")
        try:
            res_id = int(params[2])
        except ValueError:
            return
        model_name = params[1]
        if model_name not in self.env:
            return
        if len(params) == 4:
            access_token = params[3]
        else:
            access_token = None
        record = self.env[model_name].browse(res_id).exists()
        access = record._check_collaborative_spreadsheet_access("read", access_token, raise_exception=False)
        if not access:
            return
        return record
