# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models
from odoo.http import request
from odoo.http.session import check
from odoo.tools.misc import OrderedSet

from odoo.addons.bus.models.bus import BusBus, channel_with_db, dispatch
from odoo.addons.bus.tools import decode_snapshot
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

    def _prepare_subscribe_channels(self, channels):
        """Return the channels formatted for the bus dispatcher.

        :param list[str] channels: Raw channel list sent by the client.
        :raise ValueError: If any channel is not a string.
        :rtype: OrderedSet
        """
        if not all(isinstance(c, str) for c in channels):
            e = "bus.Bus only string channels are allowed."
            raise ValueError(e)
        return OrderedSet(
            channel_with_db(self.env.cr.dbname, c)
            for c in self._build_bus_channel_list(list(channels))
        )

    def _subscribe(self, data):
        if not data.get("from_snapshot"):
            _logger.warning(
                "No `from_snapshot` provided on subscribe: notifications created between "
                "the data fetch and the first subscription may be missed. Pass the `from_snapshot` "
                "of the time the data was collected to avoid this gap. See `_get_bus_session_info`",
            )
            data["from_snapshot"] = BusBus.get_current_pg_snapshot(self.env.cr)
        channels = self._prepare_subscribe_channels(data["channels"])
        dispatch.subscribe(channels, data["from_snapshot"], wsrequest.ws)
        if data["check_outdated"]:
            xmin, _, _ = decode_snapshot(data["from_snapshot"])
            from_notif_domain = [("create_xid", "<=", xmin)]
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
