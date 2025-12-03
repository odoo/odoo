# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests

from collections import defaultdict
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models
from odoo.addons.mail.tools import discuss, jwt
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.web.models.models import lazymapping

_logger = logging.getLogger(__name__)


class DiscussChannelRtcSession(models.Model):
    _name = 'discuss.channel.rtc.session'
    _inherit = ["bus.listener.mixin"]
    _description = 'Mail RTC session'
    _rec_name = 'channel_member_id'

    channel_member_id = fields.Many2one('discuss.channel.member', required=True, ondelete='cascade')
    channel_id = fields.Many2one('discuss.channel', related='channel_member_id.channel_id', store=True, readonly=True, index='btree_not_null')
    partner_id = fields.Many2one('res.partner', related='channel_member_id.partner_id', string="Partner", store=True, index=True)
    guest_id = fields.Many2one('mail.guest', related='channel_member_id.guest_id')

    write_date = fields.Datetime("Last Updated On", index=True)

    is_screen_sharing_on = fields.Boolean(string="Is sharing the screen")
    is_camera_on = fields.Boolean(string="Is sending user video")
    is_muted = fields.Boolean(string="Is microphone muted")
    is_deaf = fields.Boolean(string="Has disabled incoming sound")

    _channel_member_unique = models.Constraint(
        'UNIQUE(channel_member_id)',
        'There can only be one rtc session per channel member',
    )

    @api.model_create_multi
    def create(self, vals_list):
        stores = lazymapping(lambda bus_channel: Store(bus_channel=bus_channel))
        rtc_sessions = super().create(vals_list)
        for rtc_session in rtc_sessions:
            stores[rtc_session.channel_id].add(
                rtc_session.channel_id,
                "_store_rtc_update_fields",
                fields_params={"added": rtc_session},
            )
        for channel in rtc_sessions.channel_id.filtered(lambda c: len(c.rtc_session_ids) == 1):
            body = Markup('<div data-oe-type="call" class="o_mail_notification"></div>')
            message = channel.message_post(body=body, message_type="notification")
            # sudo - discuss.call.history: can create call history when call is created.
            self.env["discuss.call.history"].sudo().create(
                {
                    "channel_id": channel.id,
                    "start_dt": fields.Datetime.now(),
                    "start_call_message_id": message.id,
                },
            )
            stores[channel].add(message, ["call_history_ids"])
        for store in stores.values():
            store.bus_send()
        return rtc_sessions

    def unlink(self):
        stores = lazymapping(lambda channel: Store(bus_channel=channel))
        call_ended_channels = self.channel_id.filtered(lambda c: not (c.rtc_session_ids - self))
        for channel in call_ended_channels:
            # If there is no member left in the RTC call, all invitations are cancelled.
            # Note: invitation depends on field `rtc_inviting_session_id` so the cancel must be
            # done before the delete to be able to know who was invited.
            channel._rtc_cancel_invitations()
            # If there is no member left in the RTC call, we remove the SFU channel uuid as the SFU
            # server will timeout the channel. It is better to obtain a new channel from the SFU server
            # than to attempt recycling a possibly stale channel uuid.
            channel.sfu_channel_uuid = False
            channel.sfu_server_url = False
        for rtc_session in self:
            stores[rtc_session.channel_id].add(
                rtc_session.channel_id,
                "_store_rtc_update_fields",
                fields_params={"removed": rtc_session},
            )
        for rtc_session in self:
            rtc_session._bus_send(
                "discuss.channel.rtc.session/ended", {"sessionId": rtc_session.id}
            )
        # sudo - dicuss.rtc.call.history: setting the end date of the call
        # after it ends is allowed.
        domain = [("channel_id", "in", call_ended_channels.ids), ("end_dt", "=", False)]
        for history in self.env["discuss.call.history"].sudo().search(domain):
            history.end_dt = fields.Datetime.now()
            stores[history.channel_id].add(history, ["duration_hour", "end_dt"])
        for store in stores.values():
            store.bus_send()
        return super().unlink()

    def _bus_channel(self):
        return self.channel_member_id._bus_channel()

    def _update_and_broadcast(self, values):
        """ Updates the session and notifies all members of the channel
            of the change.
        """
        valid_values = {'is_screen_sharing_on', 'is_camera_on', 'is_muted', 'is_deaf'}
        self.write({key: values[key] for key in valid_values if key in values})
        store = Store(bus_channel=self.channel_id).add(self, "_store_extra_fields")
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
                payload_by_target[target_session]['notifications'].append(content)
        for target, payload in payload_by_target.items():
            target._bus_send("discuss.channel.rtc.session/peer_notification", payload)

    def _store_rtc_session_fields(self, res: Store.FieldList):
        res.one("channel_member_id", "_store_avatar_card_fields")

    def _store_extra_fields(self, res: Store.FieldList):
        self._store_rtc_session_fields(res)
        res.extend(["is_camera_on", "is_deaf", "is_muted", "is_screen_sharing_on"])

    @api.model
    def _inactive_rtc_session_domain(self):
        return [('write_date', '<', fields.Datetime.now() - relativedelta(minutes=1))]
