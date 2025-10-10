# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import models
from odoo.exceptions import AccessDenied, AccessError


class IrWebsocket(models.AbstractModel):
    _inherit = 'ir.websocket'

    def _build_bus_channel_list(self, channels):
        if self.env.uid:
            # Do not alter original list.
            channels = list(channels)
            for channel in channels:
                if isinstance(channel, str):
                    match = re.match(r'editor_collaboration:(\w+(?:\.\w+)*):(\w+):(\d+)', channel)
                    if match:
                        model_name = match[1]
                        field_name = match[2]
                        res_id = int(match[3])

                        # Verify access to the edition channel.
                        if self.env.user._is_public():
                            raise AccessDenied()

                        document = self.env[model_name].browse([res_id])
                        if not document.exists():
                            continue

                        try:
                            document.check_access('read')
                            document.check_field_access_rights('read', [field_name])
                            document.check_access('write')
                            document.check_field_access_rights('write', [field_name])
                        except AccessError:
                            continue

                        channels.append((self.env.registry.db_name, 'editor_collaboration', model_name, field_name, res_id))
        return super()._build_bus_channel_list(channels)
