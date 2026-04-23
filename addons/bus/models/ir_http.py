# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from ..websocket import WebsocketConnectionHandler


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def _get_bus_session_info(self):
        return {
            # sudo - bus.bus: reading last bus id isn't sensitive.
            "last_id": self.env["bus.bus"].sudo()._bus_last_id(),
            "worker_version": WebsocketConnectionHandler._VERSION,
        }

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        session_info["bus_info"] = self._get_bus_session_info()
        return session_info

    def session_info(self):
        session_info = super().session_info()
        session_info["bus_info"] = self._get_bus_session_info()
        return session_info
