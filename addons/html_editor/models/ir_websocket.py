import re

from odoo import models
from odoo.exceptions import AccessDenied, AccessError


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _get_bus_channels(self, channels):
        if self.env.uid:
            channels = list(channels)
            collaboration_channels = []
            for channel in channels:
                if isinstance(channel, str):
                    match = re.match(
                        r"editor_collaboration:(\w+(?:\.\w+)*):(\w+):(\d+)", channel
                    )
                    if match:
                        model_name = match[1]
                        field_name = match[2]
                        res_id = int(match[3])

                        if self.env.user._is_public():
                            raise AccessDenied

                        document = self.env[model_name].browse([res_id])
                        if not document.exists():
                            continue

                        try:
                            document.check_access("read")
                            document.check_access("write")
                            if field := document._fields.get(field_name):
                                document._check_field_access(field, "read")
                                document._check_field_access(field, "write")
                        except AccessError:
                            continue

                        collaboration_channels.append(
                            (
                                self.env.registry.db_name,
                                "editor_collaboration",
                                model_name,
                                field_name,
                                res_id,
                            )
                        )
            channels.extend(collaboration_channels)
        return super()._get_bus_channels(channels)
