# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models
from odoo.http import request
from odoo.http.session import check
from odoo.tools.misc import OrderedSet

from odoo.addons.bus.models.bus import channel_with_db, dispatch, get_current_pg_snapshot
from odoo.addons.bus.websocket import wsrequest

_logger = logging.getLogger(__name__)


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
        if not data.get("stream_position"):
            _logger.warning(
                "No `stream_position` provided on subscribe: notifications created between "
                "page load and the first subscription may be missed. The client should pass the "
                "snapshot captured at page load to avoid this gap. See `_get_bus_session_info`.",
            )
            data["stream_position"] = get_current_pg_snapshot(self.env.cr)
        if not all(isinstance(c, str) for c in data["channels"]):
            e = "bus.Bus only string channels are allowed."
            raise ValueError(e)
        all_channels = OrderedSet(channel_with_db(self.env.cr.dbname, c) for c in self._build_bus_channel_list(data["channels"]))
        dispatch.subscribe(all_channels, data["stream_position"], wsrequest.ws)
        if data["check_outdated"]:
            xmin = int(data["stream_position"].split(":")[0])
            from_notif_domain = [("create_tx_id", "<=", xmin)]
            # sudo - bus.bus: checking if last received notification still exists is acceptable.
            if self.env["bus.bus"].sudo().search_count(from_notif_domain, limit=1) == 0:
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
