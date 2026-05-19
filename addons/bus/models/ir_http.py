# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from odoo.addons.bus.models.bus import get_current_pg_snapshot
from odoo.addons.bus.websocket import WebsocketConnectionHandler


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        # Avoid querying position on every frontend page load. Bus consumers should query
        # the stream position only when actually needed. A fallback stream position is
        # captured at `ir_websocket.subscribe` time, along with a warning.
        session_info["bus_info"] = self._get_bus_session_info(with_stream_position=False)
        return session_info

    def _get_bus_session_info(self, *, with_stream_position=True):
        position = get_current_pg_snapshot(self.env.cr) if with_stream_position else None
        return {
            "stream_position": position,
            "worker_version": WebsocketConnectionHandler._VERSION,
        }

    def session_info(self):
        session_info = super().session_info()
        session_info["bus_info"] = self._get_bus_session_info()
        return session_info
