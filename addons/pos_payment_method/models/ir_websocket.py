from collections.abc import Iterable

from odoo import models
from odoo.exceptions import AccessError


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels: Iterable[str | models.BaseModel]):
        if self.env.uid:
            channels = self._add_electronic_payment_channels(channels)
        return super()._build_bus_channel_list(channels)

    def _add_electronic_payment_channels(self, channels: Iterable[str | models.BaseModel]):
        channels = list(channels)
        for channel in channels:
            if not isinstance(channel, str):
                continue
            if channel.startswith("pos.electronic.payment:"):
                record = self._check_electronic_payment_channel(channel)
                if record:
                    channels.append(record)
        return channels

    def _check_electronic_payment_channel(self, channel: str):
        try:
            res_id = int(channel.split(":")[1])
            record = self.env["pos.electronic.payment"].browse(res_id).exists()
            record._check_access()
            return record
        except (ValueError, AccessError):
            return None
