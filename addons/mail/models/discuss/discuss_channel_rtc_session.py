import logging
import typing
from collections import defaultdict
from typing import Literal, Self

import requests
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

from odoo.addons.mail.models.discuss.discuss_channel_member import AVATAR_CARD_FIELDS
from odoo.addons.mail.tools import discuss, jwt
from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput, StoreFieldSpec

if typing.TYPE_CHECKING:
    from ..res_partner import ResPartner
    from .discuss_channel import DiscussChannel
    from .discuss_channel_member import DiscussChannelMember
    from .mail_guest import MailGuest

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class DiscussChannelRtcSession(models.Model):
    _name = "discuss.channel.rtc.session"
    _inherit = ["mixin.bus.listener"]
    _description = "Mail RTC session"
    _rec_name = "channel_member_id"

    channel_member_id: DiscussChannelMember = fields.Many2one(
        comodel_name="discuss.channel.member",
        required=True,
        ondelete="cascade",
    )
    channel_id: DiscussChannel = fields.Many2one(  # noqa: E8529  One2many inverse of discuss.channel.rtc_session_ids
        comodel_name="discuss.channel",
        related="channel_member_id.channel_id",
        store=True,
        index="btree_not_null",
        readonly=True,
    )
    partner_id: ResPartner = fields.Many2one(  # noqa: E8529  One2many inverse of res.partner.rtc_session_ids
        comodel_name="res.partner",
        related="channel_member_id.partner_id",
        string="Partner",
        store=True,
        index=True,
    )
    guest_id: MailGuest = fields.Many2one(
        comodel_name="mail.guest",
        related="channel_member_id.guest_id",
    )

    write_date = fields.Datetime(
        string="Last Updated On",
        index=True,
    )

    is_screen_sharing_on = fields.Boolean(string="Is sharing the screen")
    is_camera_on = fields.Boolean(string="Is sending user video")
    is_muted = fields.Boolean(string="Is microphone muted")
    is_deaf = fields.Boolean(string="Has disabled incoming sound")

    _channel_member_unique = models.Constraint(
        "UNIQUE(channel_member_id)",
        "There can only be one rtc session per channel member",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        rtc_sessions = super().create(vals_list)
        rtc_sessions_by_channel = defaultdict(
            lambda: self.env["discuss.channel.rtc.session"]
        )
        for rtc_session in rtc_sessions:
            rtc_sessions_by_channel[rtc_session.channel_id] += rtc_session
        for channel, channel_sessions in rtc_sessions_by_channel.items():
            Store(bus_channel=channel).add(
                channel,
                {"rtc_session_ids": Store.Many(channel_sessions, mode="ADD")},
            ).bus_send()
        channels = rtc_sessions.channel_id
        if channels:
            self.env.cr.execute(
                "SELECT id FROM discuss_channel WHERE id = ANY(%s) FOR UPDATE",
                [channels.ids],
            )
            channels.invalidate_recordset(["rtc_session_ids"])
        _debug.lifecycle(
            "create",
            sessions=rtc_sessions.ids,
            channels=channels.ids,
            calls_started=len(channels.filtered(lambda c: len(c.rtc_session_ids) == 1)),
        )
        for channel in channels.filtered(lambda c: len(c.rtc_session_ids) == 1):
            body = Markup('<div data-oe-type="call" class="o_mail_notification"></div>')
            message = channel.message_post(body=body, message_type="notification")
            self.env["discuss.call.history"].sudo().create(
                {
                    "channel_id": channel.id,
                    "start_dt": fields.Datetime.now(),
                    "start_call_message_id": message.id,
                },
            )
            Store(bus_channel=channel).add(
                message, [Store.Many("call_history_ids", [])]
            ).bus_send()
        return rtc_sessions

    def unlink(self) -> Literal[True]:
        channels = self.channel_id
        if channels:
            self.env.cr.execute(
                "SELECT id FROM discuss_channel WHERE id = ANY(%s) FOR UPDATE",
                [channels.ids],
            )
            channels.invalidate_recordset(["rtc_session_ids"])
        call_ended_channels = channels.filtered(
            lambda c: not (c.rtc_session_ids - self)
        )
        _debug.lifecycle(
            "unlink",
            sessions=self.ids,
            channels=channels.ids,
            calls_ended=len(call_ended_channels),
        )
        for channel in call_ended_channels:
            channel._rtc_cancel_invitations()
            channel.sfu_channel_uuid = False
            channel.sfu_server_url = False
        rtc_sessions_by_channel = defaultdict(
            lambda: self.env["discuss.channel.rtc.session"]
        )
        for rtc_session in self:
            rtc_sessions_by_channel[rtc_session.channel_id] += rtc_session
        for channel, rtc_sessions in rtc_sessions_by_channel.items():
            Store(bus_channel=channel).add(
                channel,
                {"rtc_session_ids": Store.Many(rtc_sessions, [], mode="DELETE")},
            ).bus_send()
        for rtc_session in self:
            rtc_session._bus_send(
                "discuss.channel.rtc.session/ended", {"sessionId": rtc_session.id}
            )
        for history in (
            self.env["discuss.call.history"]
            .sudo()
            .search(
                [("channel_id", "in", call_ended_channels.ids), ("end_dt", "=", False)]
            )
        ):
            history.end_dt = fields.Datetime.now()
            Store(bus_channel=history.channel_id).add(
                history,
                ["duration_hour", "end_dt"],
            ).bus_send()
        return super().unlink()

    def _bus_channel(self) -> models.Model:
        return self.channel_member_id._bus_channel()

    def _update_and_broadcast(self, values: dict) -> None:
        valid_values = {"is_screen_sharing_on", "is_camera_on", "is_muted", "is_deaf"}
        _debug.lifecycle(
            "session_updated",
            sessions=self.ids,
            fields=sorted(valid_values & values.keys()),
            ignored=sorted(values.keys() - valid_values),
        )
        self.write({key: values[key] for key in valid_values if key in values})
        store = Store().add(self, extra_fields=self._get_fields_store_extra())
        self.channel_id._bus_send(
            "discuss.channel.rtc.session/update_and_broadcast",
            {"data": store.get_result(), "channelId": self.channel_id.id},
        )

    @api.autovacuum
    def _gc_inactive_sessions(self) -> None:
        inactive = self.search(self._get_domain_inactive_rtc_sessions())
        _debug.lifecycle("gc_inactive_sessions", removed=len(inactive))
        inactive.unlink()

    def action_disconnect(self) -> None:
        session_ids_by_channel_by_url = defaultdict(lambda: defaultdict(list))
        for rtc_session in self:
            sfu_channel_uuid = rtc_session.channel_id.sfu_channel_uuid
            url = rtc_session.channel_id.sfu_server_url
            if sfu_channel_uuid and url:
                session_ids_by_channel_by_url[url][sfu_channel_uuid].append(
                    rtc_session.id
                )
        key = discuss.get_sfu_key(self.env)
        _debug.pipeline(
            "disconnect",
            sessions=self.ids,
            sfu_servers=len(session_ids_by_channel_by_url),
            has_key=bool(key),
        )
        if key:
            with self.env["ir.egress"].session(
                purpose="discuss_sfu", policy="private"
            ) as requests_session:
                for (
                    url,
                    session_ids_by_channel,
                ) in session_ids_by_channel_by_url.items():
                    try:
                        requests_session.post(
                            url + "/v1/disconnect",
                            data=jwt.sign(
                                {"sessionIdsByChannel": session_ids_by_channel},
                                key=key,
                                ttl=20,
                                algorithm=jwt.Algorithm.HS256,
                            ),
                            timeout=3,
                        ).raise_for_status()
                    except requests.exceptions.RequestException as error:
                        _debug.logic(
                            "sfu_disconnect_failed", url=url, error=type(error).__name__
                        )
                        _logger.warning(
                            "Could not disconnect sessions at sfu server %s: %s",
                            url,
                            error,
                        )
        self.unlink()

    def _remove_inactive_rtc_sessions(self) -> None:
        self.filtered_domain(self._get_domain_inactive_rtc_sessions()).unlink()

    def _notify_peers(self, notifications: list[tuple]) -> None:
        self.check_singleton()
        payload_by_target = defaultdict(
            lambda: {"sender": self.id, "notifications": []}
        )
        for target_session_ids, content in notifications:
            for target_session in (
                self.env["discuss.channel.rtc.session"]
                .browse(target_session_ids)
                .exists()
                .filtered(lambda target: target.channel_id == self.channel_id)
            ):
                payload_by_target[target_session]["notifications"].append(content)
        _debug.pipeline(
            "peers_notified",
            session=self.id,
            notifications=len(notifications),
            targets=len(payload_by_target),
        )
        for target, payload in payload_by_target.items():
            target._bus_send("discuss.channel.rtc.session/peer_notification", payload)

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return Store.One(
            "channel_member_id",
            [
                Store.One("channel_id", [], as_thread=True),
                *self.env["discuss.channel.member"]._to_store_persona(
                    AVATAR_CARD_FIELDS
                ),
            ],
        )

    def _get_fields_store_extra(self) -> list[StoreFieldSpec]:
        return ["is_camera_on", "is_deaf", "is_muted", "is_screen_sharing_on"]

    @api.model
    def _get_domain_inactive_rtc_sessions(self) -> list:
        return [
            (
                "write_date",
                "<",
                fields.Datetime.now() - relativedelta(minutes=1, seconds=15),
            )
        ]
