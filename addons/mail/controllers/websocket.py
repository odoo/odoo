from odoo.addons.bus.controllers.websocket import WebsocketController
from odoo.http import request, route, SessionExpiredException


class WebsocketControllerPresence(WebsocketController):
    @route("/websocket/update_bus_presence", type="jsonrpc", auth="public", cors="*")
    def update_bus_presence(self, inactivity_period):
        if "is_websocket_session" not in request.session:
            raise SessionExpiredException()
        request.env["ir.websocket"]._update_bus_presence(int(inactivity_period))
        return {}

    @route()
    def peek_notifications(self, channels, last, is_first_poll=False):
        bus_channels = request.env["ir.websocket"]._build_bus_channel_list(channels)
        request.env["ir.websocket"]._dispatch_missed_presences(bus_channels)
        return super().peek_notifications(channels, last, is_first_poll=is_first_poll)
