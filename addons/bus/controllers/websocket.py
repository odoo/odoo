# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route
from ..websocket import WebsocketConnectionHandler


class WebsocketController(Controller):
    @route('/websocket', type="http", auth="public", cors='*', websocket=True)
    def websocket(self):
        """
        Handle the websocket handshake, upgrade the connection if
        successfull.
        """
        return WebsocketConnectionHandler.open_connection(request)
