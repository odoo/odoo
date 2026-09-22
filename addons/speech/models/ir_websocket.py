import re

from odoo import models

LIVE_CHANNEL = re.compile(r"^speech\.live/([a-z0-9_.]+)/(\d+)$")


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _get_bus_channels(self, channels):
        live, others = {}, []
        for channel in channels:
            match = LIVE_CHANNEL.match(channel) if isinstance(channel, str) else None
            if match and self._is_live_model(match.group(1)):
                live.setdefault(match.group(1), []).append(int(match.group(2)))
            else:
                others.append(channel)
        result = super()._get_bus_channels(others)
        for model, ids in live.items():
            records = self.env[model].browse(ids).exists()
            result.extend(
                (record, "live") for record in records._filtered_access("read")
            )
        return result

    def _is_live_model(self, model: str) -> bool:
        registry = self.env.registry
        return model in registry and issubclass(
            registry[model], registry["mixin.media.live"]
        )
