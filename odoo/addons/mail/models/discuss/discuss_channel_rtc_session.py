# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.addons.mail.tools import discuss, jwt

_logger = logging.getLogger(__name__)


class MailRtcSession(models.Model):
    _name = 'discuss.channel.rtc.session'
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
        self.env['bus.bus']._sendmany([(channel, 'discuss.channel/rtc_sessions_update', {
            'id': channel.id,
            'rtcSessions': [('ADD', sessions_data)],
        }) for channel, sessions_data in rtc_sessions._mail_rtc_session_format_by_channel().items()])
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
        notifications = [(channel, 'discuss.channel/rtc_sessions_update', {
            'id': channel.id,
            'rtcSessions': [('DELETE', [{'id': session_data['id']} for session_data in sessions_data])],
        }) for channel, sessions_data in self._mail_rtc_session_format_by_channel().items()]
        for rtc_session in self:
            target = rtc_session.guest_id or rtc_session.partner_id
            notifications.append((target, 'discuss.channel.rtc.session/ended', {'sessionId': rtc_session.id}))
        self.env['bus.bus']._sendmany(notifications)
        return super().unlink()

    def _update_and_broadcast(self, values):
        """ Updates the session and notifies all members of the channel
            of the change.
        """
        valid_values = {'is_screen_sharing_on', 'is_camera_on', 'is_muted', 'is_deaf'}
        self.write({key: values[key] for key in valid_values if key in values})
        session_data = self._mail_rtc_session_format(extra=True)
        self.env["bus.bus"]._sendone(
            self.channel_id,
            "discuss.channel.rtc.session/update_and_broadcast",
            {"data": session_data, "channelId": self.channel_id.id},
        )

    @api.autovacuum
    def _gc_inactive_sessions(self):
        """ Garbage collect sessions that aren't active anymore,
            this can happen when the server or the user's browser crash
            or when the user's odoo session ends.
        """
        self.search(self._inactive_rtc_session_domain()).unlink()

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
                target = target_session.guest_id or target_session.partner_id
                payload_by_target[target]['notifications'].append(content)
        return self.env['bus.bus']._sendmany([(target, 'discuss.channel.rtc.session/peer_notification', payload) for target, payload in payload_by_target.items()])

    def _mail_rtc_session_format(self, extra=False):
        self.ensure_one()
        vals = {
            "id": self.id,
            "channelMember": self.channel_member_id._discuss_channel_member_format(
                fields={
                    "id": True,
                    "channel": {},
                    "persona": {"partner": {"id", "name", "im_status"}, "guest": {"id", "name", "im_status"}},
                }
            ).get(self.channel_member_id),
        }
        if extra:
            vals.update({
                "isCameraOn": self.is_camera_on,
                "isDeaf": self.is_deaf,
                "isSelfMuted": self.is_muted,
                "isScreenSharingOn": self.is_screen_sharing_on,
            })
        return vals

    def _mail_rtc_session_format_by_channel(self, extra=False):
        data = {}
        for rtc_session in self:
            data.setdefault(rtc_session.channel_id, []).append(rtc_session._mail_rtc_session_format(extra=extra))
        return data

    @api.model
    def _inactive_rtc_session_domain(self):
        return [('write_date', '<', fields.Datetime.now() - relativedelta(minutes=1))]
