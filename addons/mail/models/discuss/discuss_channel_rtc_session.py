# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.addons.mail.tools import discuss, jwt
from odoo.addons.mail.tools.discuss import Store

_logger = logging.getLogger(__name__)


class MailRtcSession(models.Model):
    _name = 'discuss.channel.rtc.session'
    _inherit = ["bus.listener.mixin"]
    _description = 'Mail RTC session'
    _rec_name = 'channel_member_id'

    channel_member_id = fields.Many2one('discuss.channel.member', required=True, ondelete='cascade')
    channel_id = fields.Many2one('discuss.channel', related='channel_member_id.channel_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', related='channel_member_id.partner_id', string="Partner")
    guest_id = fields.Many2one('mail.guest', related='channel_member_id.guest_id')

    write_date = fields.Datetime("Last Updated On", index=True)

    is_screen_sharing_on = fields.Boolean(string="Is sharing the screen")
    is_camera_on = fields.Boolean(string="Is sending user video")
    is_muted = fields.Boolean(string="Is microphone muted")
    is_deaf = fields.Boolean(string="Has disabled incoming sound")

    _sql_constraints = [
        ('channel_member_unique', 'UNIQUE(channel_member_id)',
         'There can only be one rtc session per channel member')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        rtc_sessions = super().create(vals_list)
        rtc_sessions_by_channel = defaultdict(lambda: self.env["discuss.channel.rtc.session"])
        for rtc_session in rtc_sessions:
            rtc_sessions_by_channel[rtc_session.channel_id] += rtc_session
        for channel, rtc_sessions in rtc_sessions_by_channel.items():
            channel._bus_send_store(channel, {"rtcSessions": Store.many(rtc_sessions, "ADD")})
        return rtc_sessions

    def unlink(self):
        channels = self.channel_id
        for channel in channels:
            if channel.rtc_session_ids and len(channel.rtc_session_ids - self) == 0:
                # If there is no member left in the RTC call, all invitations are cancelled.
                # Note: invitation depends on field `rtc_inviting_session_id` so the cancel must be
                # done before the delete to be able to know who was invited.
                channel._rtc_cancel_invitations()
                # If there is no member left in the RTC call, we remove the SFU channel uuid as the SFU
                # server will timeout the channel. It is better to obtain a new channel from the SFU server
                # than to attempt recycling a possibly stale channel uuid.
                channel.sfu_channel_uuid = False
                channel.sfu_server_url = False
        rtc_sessions_by_channel = defaultdict(lambda: self.env["discuss.channel.rtc.session"])
        for rtc_session in self:
            rtc_sessions_by_channel[rtc_session.channel_id] += rtc_session
        for channel, rtc_sessions in rtc_sessions_by_channel.items():
            channel._bus_send_store(
                channel, {"rtcSessions": Store.many(rtc_sessions, "DELETE", only_id=True)}
            )
        for rtc_session in self:
            rtc_session._bus_send(
                "discuss.channel.rtc.session/ended", {"sessionId": rtc_session.id}
            )
        return super().unlink()

    def _bus_channel(self):
        return self.channel_member_id._bus_channel()

    def _update_and_broadcast(self, values):
        """ Updates the session and notifies all members of the channel
            of the change.
        """
        valid_values = {'is_screen_sharing_on', 'is_camera_on', 'is_muted', 'is_deaf'}
        self.write({key: values[key] for key in valid_values if key in values})
        store = Store(self, extra=True)
        self.channel_id._bus_send(
            "discuss.channel.rtc.session/update_and_broadcast",
            {"data": store.get_result(), "channelId": self.channel_id.id},
        )

    @api.autovacuum
    def _gc_inactive_sessions(self):
        """ Garbage collect sessions that aren't active anymore,
            this can happen when the server or the user's browser crash
            or when the user's odoo session ends.
        """
        self.search(self._inactive_rtc_session_domain(), limit=10000).unlink()

    def action_disconnect(self):
        session_ids_by_channel_by_url = defaultdict(lambda: defaultdict(list))
        for rtc_session in self:
            sfu_channel_uuid = rtc_session.channel_id.sfu_channel_uuid
            url = rtc_session.channel_id.sfu_server_url
            if sfu_channel_uuid and url:
                session_ids_by_channel_by_url[url][sfu_channel_uuid].append(rtc_session.id)
        key = discuss.get_sfu_key(self.env)
        if key:
            with requests.Session() as requests_session:
                for url, session_ids_by_channel in session_ids_by_channel_by_url.items():
                    try:
                        requests_session.post(
                            url + '/v1/disconnect',
                            data=jwt.sign({'sessionIdsByChannel': session_ids_by_channel}, key=key, ttl=20, algorithm=jwt.Algorithm.HS256),
                            timeout=3
                        ).raise_for_status()
                    except requests.exceptions.RequestException as error:
                        _logger.warning("Could not disconnect sessions at sfu server %s: %s", url, error)
        self.unlink()

    def _delete_inactive_rtc_sessions(self):
        """Deletes the inactive sessions from self."""
        self.filtered_domain(self._inactive_rtc_session_domain()).unlink()

    def _notify_peers(self, notifications):
        """ Used for peer-to-peer communication,
            guarantees that the sender is the current guest or partner.

            :param notifications: list of tuple with the following elements:
                - target_session_ids: a list of discuss.channel.rtc.session ids
                - content: a string with the content to be sent to the targets
        """
        self.ensure_one()
        payload_by_target = defaultdict(lambda: {'sender': self.id, 'notifications': []})
        for target_session_ids, content in notifications:
            for target_session in self.env['discuss.channel.rtc.session'].browse(target_session_ids).exists():
                payload_by_target[target_session]['notifications'].append(content)
        for target, payload in payload_by_target.items():
            target._bus_send("discuss.channel.rtc.session/peer_notification", payload)

    def _to_store(self, store: Store, extra=False):
        for rtc_session in self:
            data = rtc_session._read_format([], load=False)[0]
            data["channelMember"] = Store.one(
                rtc_session.channel_member_id,
                fields={"channel": [], "persona": ["name", "im_status"]},
            )
            if extra:
                data.update(
                    {
                        "isCameraOn": rtc_session.is_camera_on,
                        "isDeaf": rtc_session.is_deaf,
                        "isSelfMuted": rtc_session.is_muted,
                        "isScreenSharingOn": rtc_session.is_screen_sharing_on,
                    }
                )
            store.add(rtc_session, data)

    @api.model
    def _inactive_rtc_session_domain(self):
        return [('write_date', '<', fields.Datetime.now() - relativedelta(minutes=1))]
