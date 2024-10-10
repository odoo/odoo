# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request, SessionExpiredException
from odoo.service import security
from odoo.addons.bus.models.bus import dispatch
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
        channels.extend(self.env.user.groups_id)
        if req.session.uid:
            channels.append(self.env.user.partner_id)
        return channels

    def _prepare_subscribe_data(self, channels, last):
        """
        Parse the data sent by the client and return the list of channels
        and the last known notification id. This will be used both by the
        websocket controller and the websocket request class when the
        `subscribe` event is received.

        :param typing.List[str] channels: List of channels to subscribe to sent
            by the client.
        :param int last: Last known notification sent by the client.

        :return:
            A dict containing the following keys:
            - channels (set of str): The list of channels to subscribe to.
            - last (int): The last known notification id.

        :raise ValueError: If the list of channels is not a list of strings.
        """
        if not all(isinstance(c, str) for c in channels):
            raise ValueError("bus.Bus only string channels are allowed.")
        # sudo - bus.bus: reading non-sensitive last bus id.
        last = 0 if last > self.env["bus.bus"].sudo()._bus_last_id() else last
        return {"channels": channels, "last": last}

    def _subscribe(self, og_data):
        data = self._prepare_subscribe_data(og_data["channels"], og_data["last"])
        dispatch.subscribe(data["channels"], data["last"], self.env.registry.db_name, wsrequest.ws)

    def _update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        """
            Update the presence information of users on the bus.

            - This method is hardcoded to be one of the few methods that can be called via the websocket
            route due to Odoo's architecture and its use of proxying on odoo.sh.
            - The restriction ensures that only essential methods are exposed to save server resources
            and avoid unnecessary polling.

            :param int inactivity_period: The period (in milliseconds) since last user activity.
            :param dict im_status_ids_by_model: A dictionary containing IM status IDs referenced by model.
        """

    def _on_websocket_closed(self, cookies):
        """
            Handle the closure of a websocket connection.

            This method is invoked by the `websocket.py` module when a websocket connection is closed.
            The primary purpose of this method is to perform any necessary cleanup or state updates
            when a websocket connection terminates.
        """

    @classmethod
    def _authenticate(cls):
        if wsrequest.session.uid is not None:
            if not security.check_session(wsrequest.session, wsrequest.env, wsrequest):
                wsrequest.session.logout(keep_db=True)
                raise SessionExpiredException()
        else:
            public_user = wsrequest.env.ref('base.public_user')
            wsrequest.update_env(user=public_user.id)
