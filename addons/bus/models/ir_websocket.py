# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
from odoo.http.session import check
from odoo.tools.misc import OrderedSet
from ..models.bus import dispatch
from ..websocket import wsrequest


class IrWebsocket(models.AbstractModel):
    _name = 'ir.websocket'
    _description = 'websocket message handling'

    def _build_bus_channel_list(self, channels):
        """
            Return the list of channels to subscribe to. Override this
            method to add channels in addition to the ones the client
            sent.

            :param channels: The channel list sent by the client.
        """
        req = request or wsrequest
        channels.append('broadcast')
        channels.extend(self.env.user.all_group_ids)
        if req.session.uid:
            channels.append(self.env.user.partner_id)
            channels.append(self.env.user)
        return channels

    def _serve_ir_websocket(self, event_name, data):
        """Process websocket events.
        Modules can override this method to handle their own events. But overriding this method is
        not recommended and should be carefully considered, because at the time of writing this
        message, Odoo.sh does not use this method. Each new event should have a corresponding http
        route and Odoo.sh infrastructure should be updated to reflect it. On top of that, the
        event processing is very time, ressource and error sensitive."""

    def _subscribe(self, data):
        if not all(isinstance(c, str) for c in data["channels"]):
            e = "bus.Bus only string channels are allowed."
            raise ValueError(e)
        all_channels = OrderedSet(self._build_bus_channel_list(data["channels"]))
        dispatch.subscribe(all_channels, data["last"], self.env.registry.db_name, wsrequest.ws)
        # sudo - bus.bus: checking if last received notification still exists is acceptable.
        if data["check_outdated"] and not self.env["bus.bus"].sudo().search(
            [("id", "=", data["last"])],
        ):
            wsrequest.ws.send_worker_internal_message("bus/subscription_outdated")

    def _on_websocket_closed(self, cookies):
        """Function invoked upon WebSocket termination.
        Modules can override this method to add custom behavior."""

    @classmethod
    def _authenticate(cls):
        if wsrequest.session.uid is not None:
            check(wsrequest.session, wsrequest)
        else:
            public_user = wsrequest.env.ref('base.public_user')
            wsrequest.update_env(user=public_user.id)
