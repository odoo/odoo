# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from ..websocket import WebsocketConnectionHandler
from odoo.addons import web


class IrHttp(web.IrHttp):

    @api.model
    def get_frontend_session_info(self):
        session_info = super().get_frontend_session_info()
        session_info["websocket_worker_version"] = WebsocketConnectionHandler._VERSION
        return session_info

    def session_info(self):
        session_info = super().session_info()
        session_info["websocket_worker_version"] = WebsocketConnectionHandler._VERSION
        return session_info
