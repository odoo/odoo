# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from odoo.addons.bus.models.bus import BusBus
from odoo.addons.bus.websocket import WebsocketConnectionHandler


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        # Avoid capturing snapshot on every frontend page load. Bus consumers should
        # request it only when actually needed. A fallback snapshot is captured at
        # `ir_websocket.subscribe` time, along with a warning.
        session_info["bus_info"] = self._get_bus_session_info(with_snapshot=False)
        return session_info

    def _get_bus_session_info(self, *, with_snapshot=True):
        snapshot = BusBus.get_current_pg_snapshot(self.env.cr) if with_snapshot else None
        return {
            "initial_snapshot": snapshot,
            "worker_version": WebsocketConnectionHandler._VERSION,
        }

    def session_info(self):
        session_info = super().session_info()
        session_info["bus_info"] = self._get_bus_session_info()
        return session_info
