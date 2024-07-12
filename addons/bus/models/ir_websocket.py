from odoo import models
from odoo.http import request, SessionExpiredException
from odoo.service import security
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
        channels.extend(self.env.user.groups_id)
        if req.session.uid:
            channels.append(self.env.user.partner_id)
        return channels

    def _subscribe(self, data):
        if not all(isinstance(c, str) for c in data['channels']):
            raise ValueError("bus.Bus only string channels are allowed.")
        last_known_notification_id = self.env['bus.bus'].sudo().search([], limit=1, order='id desc').id or 0
        if data['last'] > last_known_notification_id:
            data['last'] = 0
        channels = set(self._build_bus_channel_list(data['channels']))
        dispatch.subscribe(channels, data['last'], self.env.registry.db_name, wsrequest.ws)

    def _update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        if self.env.user and not self.env.user._is_public():
            self.env['bus.presence'].update_presence(
                inactivity_period,
                identity_field='user_id',
                identity_value=self.env.uid
            )

    @classmethod
    def _authenticate(cls):
        if wsrequest.session.uid is not None:
            if not security.check_session(wsrequest.session, wsrequest.env):
                wsrequest.session.logout(keep_db=True)
                raise SessionExpiredException()
        else:
            public_user = wsrequest.env.ref('base.public_user')
            wsrequest.update_env(user=public_user.id)
