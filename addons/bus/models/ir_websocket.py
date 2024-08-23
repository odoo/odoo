from datetime import datetime, timedelta

from odoo import models
from odoo.http import request, SessionExpiredException
from odoo.tools import OrderedSet
from odoo.osv import expression
from odoo.service import security
from ..models.bus import dispatch
from ..websocket import wsrequest


class IrWebsocket(models.AbstractModel):
    _name = 'ir.websocket'
    _description = 'websocket message handling'

    def _get_im_status(self, im_status_ids_by_model):
        im_status = {}
        if 'res.partner' in im_status_ids_by_model:
            im_status['Persona'] = [{**p, 'type': "partner"} for p in self.env['res.partner'].with_context(active_test=False).search_read(
                [('id', 'in', im_status_ids_by_model['res.partner'])],
                ['im_status']
            )]
        return im_status

    def _get_missed_presences_identity_domains(self, presence_channels):
        """
        Return a list of domains that will be combined with `expression.OR` to
        find presences related to `presence_channels`. This is used to find
        missed presences when subscribing to presence channels.
        :param typing.List[typing.Tuple[recordset, str]] presence_channels: The
            presence channels the user subscribed to.
        """
        partners = self.env["res.partner"].browse(
            [p.id for p, _ in presence_channels if isinstance(p, self.pool["res.partner"])]
        )
        # sudo: res.partner - can acess users of partner channels to find
        # their presences as those channels were already verified during
        # `_build_bus_channel_list`.
        return [[("user_id", "in", partners.with_context(active_test=False).sudo().user_ids.ids)]]

    def _get_missed_presences_bus_target(self):
        return (
            self.env.user.partner_id if self.env.user and not self.env.user._is_public() else None
        )

    def _build_presence_channel_list(self, presences):
        """
        Return the list of presences to subscribe to.
        :param typing.List[typing.Tuple[str, int]] presences: The presence
            list sent by the client where the first element is the model
            name and the second is the record id.
        """
        channels = []
        if self.env.user and self.env.user._is_internal():
            channels.extend(
                (partner, "presence")
                for partner in self.env["res.partner"]
                .with_context(active_test=False)
                .search([("id", "in", [int(p[1]) for p in presences if p[0] == "res.partner"])])
            )
        return channels

    def _build_bus_channel_list(self, channels):
        """
            Return the list of channels to subscribe to. Override this
            method to add channels in addition to the ones the client
            sent.

            :param channels: The channel list sent by the client.
        """
        req = request or wsrequest
        channels.append('broadcast')
        if req.session.uid:
            channels.append(self.env.user.partner_id)
        return channels

    def _prepare_subscribe_data(self, channels, last):
        """
        Parse the data sent by the client and return the list of channels,
        missed presences and the last known notification id. This will be used
        both by the websocket controller and the websocket request class when
        the `subscribe` event is received.
        :param typing.List[str] channels: List of channels to subscribe to sent
            by the client.
        :param int last: Last known notification sent by the client.
        :return:
            A dict containing the following keys:
            - channels (set of str): The list of channels to subscribe to.
            - last (int): The last known notification id.
            - missed_presences (odoo.models.Recordset): The missed presences.
        :raise ValueError: If the list of channels is not a list of strings.
        """
        if not all(isinstance(c, str) for c in channels):
            raise ValueError("bus.Bus only string channels are allowed.")
        # sudo - bus.bus: reading non-sensitive last bus id.
        last = 0 if last > self.env["bus.bus"].sudo()._bus_last_id() else last
        str_presence_channels = {
            c for c in channels if isinstance(c, str) and c.startswith("odoo-presence-")
        }
        presence_channels = self._build_presence_channel_list(
            [tuple(c.replace("odoo-presence-", "").split("_")) for c in str_presence_channels]
        )
        # There is a gap between a subscription client side (which is debounced)
        # and the actual subcription thus presences can be missed. Send a
        # notification to avoid missing presences during a subscription.
        domain = expression.AND(
            [
                [("last_poll", ">", datetime.now() - timedelta(seconds=2))],
                expression.OR(self._get_missed_presences_identity_domains(presence_channels)),
            ]
        )
        # sudo: bus.presence: can access presences linked to presence channels.
        missed_presences = self.env["bus.presence"].sudo().search(domain)
        all_channels = OrderedSet(presence_channels)
        all_channels.update(
            self._build_bus_channel_list([c for c in channels if c not in str_presence_channels])
        )
        return {"channels": all_channels, "last": last, "missed_presences": missed_presences}

    def _subscribe(self, og_data):
        data = self._prepare_subscribe_data(og_data["channels"], og_data["last"])
        dispatch.subscribe(data["channels"], data["last"], self.env.registry.db_name, wsrequest.ws)
        if bus_target := self._get_missed_presences_bus_target():
            data["missed_presences"]._send_presence(bus_target=bus_target)

    def _update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        if self.env.user and not self.env.user._is_public():
            self.env['bus.presence'].update_presence(
                inactivity_period,
                identity_field='user_id',
                identity_value=self.env.uid
            )

    def _on_websocket_closed(self, cookies):
        if self.env.user and not self.env.user._is_public():
            self.env["bus.presence"].search([("user_id", "=", self.env.uid)]).status = "offline"

    @classmethod
    def _authenticate(cls):
        if wsrequest.session.uid is not None:
            if not security.check_session(wsrequest.session, wsrequest.env):
                wsrequest.session.logout(keep_db=True)
                raise SessionExpiredException()
        else:
            public_user = wsrequest.env.ref('base.public_user')
            wsrequest.update_env(user=public_user.id)
