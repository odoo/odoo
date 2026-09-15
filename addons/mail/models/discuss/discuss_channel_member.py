import logging
import typing
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime, timedelta
from types import NotImplementedType
from typing import Any, Literal, Self

import requests
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, Query, format_list, html_escape

from ...tools import discuss, jwt
from odoo.addons.mail.tools.discuss import Store, StoreFieldsInput, StoreFieldSpec
from odoo.addons.mail.tools.web_push import (
    PUSH_NOTIFICATION_ACTION,
    PUSH_NOTIFICATION_TYPE,
)

if typing.TYPE_CHECKING:
    from ..mail_message import MailMessage
    from ..res_partner import ResPartner
    from .discuss_channel import DiscussChannel
    from .discuss_channel_rtc_session import DiscussChannelRtcSession
    from .mail_guest import MailGuest

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)
SFU_MODE_THRESHOLD = 3
AVATAR_CARD_FIELDS = ["avatar_128", "im_status", "name"]


def escape_like_wildcards(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class DiscussChannelMember(models.Model):
    _name = "discuss.channel.member"
    _inherit = ["mixin.store.sync"]
    _description = "Channel Member"
    _rec_names_search = ["channel_id", "partner_id", "guest_id"]
    _bypass_create_check = {}

    partner_id: ResPartner = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        ondelete="cascade",
    )
    guest_id: MailGuest = fields.Many2one(
        comodel_name="mail.guest",
        index=True,
        ondelete="cascade",
    )
    is_self = fields.Boolean(
        compute="_compute_is_self",
        search="_search_is_self",
    )
    channel_id: DiscussChannel = fields.Many2one(
        comodel_name="discuss.channel",
        required=True,
        ondelete="cascade",
        bypass_search_access=True,
    )
    custom_channel_name = fields.Char(string="Custom channel name")
    fetched_message_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        string="Last Fetched",
        index="btree_not_null",
    )
    seen_message_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        string="Last Seen",
        index="btree_not_null",
    )
    new_message_separator = fields.Integer(
        default=0,
        required=True,
        help="Message id before which the separator should be displayed",
    )
    message_unread_counter = fields.Integer(
        string="Unread Messages Counter",
        compute="_compute_message_unread_counter",
        compute_sudo=True,
    )
    custom_notifications = fields.Selection(
        selection=[
            ("all", "All Messages"),
            ("mentions", "Mentions Only"),
            ("no_notif", "Nothing"),
        ],
        string="Customized Notifications",
        help="Use default from user settings if not specified. This setting will only be applied to channels.",
    )
    mute_until_dt = fields.Datetime(
        string="Mute notifications until",
        help="If set, the member will not receive notifications from the channel until this date.",
    )
    is_pinned = fields.Boolean(
        string="Is pinned on the interface",
        compute="_compute_is_pinned",
        search="_search_is_pinned",
    )
    unpin_dt = fields.Datetime(
        string="Unpin date",
        index=True,
        help="Contains the date and time when the channel was unpinned by the user.",
    )
    last_interest_dt = fields.Datetime(
        string="Last Interest",
        default=lambda self: fields.Datetime.now() - timedelta(seconds=1),
        index=True,
        help="Contains the date and time of the last interesting event that happened in this channel for this user. This includes: creating, joining, pinning",
    )
    last_seen_dt = fields.Datetime(string="Last seen date")
    rtc_session_ids: DiscussChannelRtcSession = fields.One2many(
        comodel_name="discuss.channel.rtc.session",
        inverse_name="channel_member_id",
        string="RTC Sessions",
    )
    rtc_inviting_session_id: DiscussChannelRtcSession = fields.Many2one(
        comodel_name="discuss.channel.rtc.session",
        string="Ringing session",
    )

    _seen_message_id_idx = models.Index("(channel_id, partner_id, seen_message_id)")

    @api.autovacuum
    def _gc_unpin_outdated_sub_channels(self) -> None:
        outdated_dt = fields.Datetime.now() - timedelta(days=2)
        self.env["discuss.channel"].flush_model()
        self.env["discuss.channel.member"].flush_model()
        self.env["mail.message"].flush_model()
        self.env.cr.execute(
            """
            SELECT member.id
              FROM discuss_channel_member member
              JOIN discuss_channel channel
                ON channel.id = member.channel_id
               AND channel.parent_channel_id IS NOT NULL
             WHERE COALESCE(member.last_interest_dt, member.create_date) < %(outdated_dt)s
               AND COALESCE(channel.last_interest_dt, channel.create_date) < %(outdated_dt)s
               AND NOT EXISTS (
                   SELECT 1
                     FROM mail_message
                    WHERE mail_message.res_id = channel.id
                      AND mail_message.model = 'discuss.channel'
                      AND mail_message.id >= member.new_message_separator
                      AND mail_message.message_type NOT IN ('notification', 'user_notification')
               )
            """,
            {"outdated_dt": outdated_dt},
        )
        members = self.env["discuss.channel.member"].search(
            [
                ("id", "in", [row[0] for row in self.env.cr.fetchall()]),
                ("is_pinned", "=", True),
            ],
        )
        members.unpin_dt = fields.Datetime.now()
        _debug.lifecycle("gc_sub_channels_unpinned", members=len(members))
        for member in members:
            Store(bus_channel=member._bus_channel()).add(
                member.channel_id, {"close_chat_window": True}
            ).bus_send()

    @api.constrains("partner_id")
    def _contrains_no_public_member(self) -> None:
        for member in self:
            if any(user._is_public() for user in member.partner_id.user_ids):
                raise ValidationError(_("Channel members cannot include public users."))

    @api.depends_context("uid", "guest")
    def _compute_is_self(self) -> None:
        if not self:
            return
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        self.is_self = False
        for member in self:
            if current_partner and member.partner_id == current_partner:
                member.is_self = True
            if current_guest and member.guest_id == current_guest:
                member.is_self = True

    def _search_is_self(
        self, operator: str, operand: Any
    ) -> Domain | NotImplementedType:
        if operator != "in":
            return NotImplemented
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        domain_partner = (
            Domain("partner_id", "=", current_partner.id)
            if current_partner
            else Domain.FALSE
        )
        domain_guest = (
            Domain("guest_id", "=", current_guest.id) if current_guest else Domain.FALSE
        )
        return domain_partner | domain_guest

    def _search_is_pinned(
        self, operator: str, operand: Any
    ) -> Domain | NotImplementedType:
        if operator != "in":
            return NotImplemented

        def custom_pinned(model: models.BaseModel, alias: str, query: Query) -> SQL:
            channel_model = model.browse().channel_id
            channel_alias = query.get_table_alias(alias, "channel_id")
            query.add_join(
                "LEFT JOIN",
                channel_alias,
                channel_model._table,
                SQL(
                    "%s = %s",
                    model._field_to_sql(alias, "channel_id"),
                    channel_model._field_to_sql(channel_alias, "id"),
                ),
            )
            return SQL(
                """(%(unpin)s IS NULL
                    OR %(last_interest)s >= %(unpin)s
                    OR %(channel_last_interest)s >= %(unpin)s
                )""",
                unpin=model._field_to_sql(alias, "unpin_dt", query),
                last_interest=model._field_to_sql(alias, "last_interest_dt", query),
                channel_last_interest=channel_model._field_to_sql(
                    channel_alias, "last_interest_dt", query
                ),
            )

        return Domain.custom(to_sql=custom_pinned)

    @api.depends("channel_id.message_ids", "new_message_separator")
    def _compute_message_unread_counter(self) -> None:
        if self.ids:
            self.env["mail.message"].flush_model()
            self.flush_recordset(["channel_id", "new_message_separator"])
            self.env.cr.execute(
                """
                     SELECT count(mail_message.id) AS count,
                            discuss_channel_member.id
                       FROM mail_message
                 INNER JOIN discuss_channel_member
                         ON discuss_channel_member.channel_id = mail_message.res_id
                      WHERE mail_message.model = 'discuss.channel'
                        AND mail_message.message_type NOT IN ('notification', 'user_notification')
                        AND mail_message.id >= discuss_channel_member.new_message_separator
                        AND discuss_channel_member.id = ANY(%(ids)s)
                   GROUP BY discuss_channel_member.id
            """,
                {"ids": list(self.ids)},
            )
            unread_counter_by_member = {
                res["id"]: res["count"] for res in self.env.cr.dictfetchall()
            }
            for member in self:
                member.message_unread_counter = unread_counter_by_member.get(
                    member.id, 0
                )
        else:
            self.message_unread_counter = 0

    @api.depends("partner_id.name", "guest_id.name", "channel_id.display_name")
    def _compute_display_name(self) -> None:
        for member in self:
            member.display_name = _(
                "“%(member_name)s” in “%(channel_name)s”",
                member_name=member.partner_id.name or member.guest_id.name,
                channel_name=member.channel_id.display_name,
            )

    @api.depends("last_interest_dt", "unpin_dt", "channel_id.last_interest_dt")
    def _compute_is_pinned(self) -> None:
        for member in self:
            member.is_pinned = (
                not member.unpin_dt
                or (
                    member.last_interest_dt
                    and member.last_interest_dt >= member.unpin_dt
                )
                or (
                    member.channel_id.last_interest_dt
                    and member.channel_id.last_interest_dt >= member.unpin_dt
                )
            )

    _partner_unique = models.UniqueIndex(
        "(channel_id, partner_id) WHERE partner_id IS NOT NULL"
    )
    _guest_unique = models.UniqueIndex(
        "(channel_id, guest_id) WHERE guest_id IS NOT NULL"
    )
    _partner_or_guest_exists = models.Constraint(
        "CHECK((partner_id IS NOT NULL AND guest_id IS NULL) OR (partner_id IS NULL AND guest_id IS NOT NULL))",
        "A channel member must be a partner or a guest.",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        if (
            self.env.context.get("mail_create_bypass_create_check")
            is self._bypass_create_check
        ):
            self = self.sudo()
        if any("channel_id" not in vals for vals in vals_list):
            raise UserError(
                _(
                    "It appears you're trying to create a channel member, but it seems like you forgot to specify the related channel. "
                    "To move forward, please make sure to provide the necessary channel information."
                )
            )
        added_by_channel = Counter(vals["channel_id"] for vals in vals_list)
        name_members_by_channel = {
            channel: channel.channel_name_member_ids
            for channel in self.env["discuss.channel"].browse(set(added_by_channel))
        }
        for channel in name_members_by_channel:
            channel._check_chat_capacity(
                channel.channel_type,
                len(channel.channel_member_ids) + added_by_channel[channel.id],
            )
        res = super().create(vals_list)
        res.partner_id.invalidate_recordset(["channel_ids"])
        res.guest_id.invalidate_recordset(["channel_ids"])
        members_by_parent = defaultdict(self.browse)
        for member in res:
            if parent := member.channel_id.parent_channel_id:
                members_by_parent[parent] |= member
        _debug.lifecycle(
            "create",
            count=len(res),
            channels=len(added_by_channel),
            parents=len(members_by_parent),
            sudo=self.env.su,
        )
        for parent, members in members_by_parent.items():
            parent._add_members(partners=members.partner_id, guests=members.guest_id)
        for channel, members in name_members_by_channel.items():
            if channel.channel_name_member_ids != members:
                Store(bus_channel=channel).add(
                    channel,
                    Store.Many("channel_name_member_ids", sort="id"),
                ).bus_send()
        return res

    def write(self, vals: ValuesType) -> Literal[True]:
        for channel_member in self:
            for field_name in ["channel_id", "partner_id", "guest_id"]:
                if (
                    field_name in vals
                    and vals[field_name] != channel_member[field_name].id
                ):
                    raise AccessError(
                        _("You can not write on %(field_name)s.", field_name=field_name)
                    )

        sync_field_names, old_vals = self._prepare_sync_snapshot(vals)
        result = super().write(vals)
        _debug.lifecycle(
            "write",
            members=self.ids,
            fields=list(vals),
            synced=sorted(str(name) for name in sync_field_names),
        )
        self._notify_sync_diffs(sync_field_names, old_vals)
        return result

    def _sync_field_names(self) -> defaultdict[str | None, list[StoreFieldSpec]]:
        res = defaultdict(list)
        res[None] += [
            "custom_channel_name",
            "custom_notifications",
            "last_interest_dt",
            "message_unread_counter",
            "mute_until_dt",
            "new_message_separator",
            Store.One(
                "rtc_inviting_session_id",
                extra_fields=self.rtc_inviting_session_id._get_fields_store_extra(),
                sudo=True,
            ),
            "unpin_dt",
        ]
        return res

    def _sync_diff_extra_fields(
        self, record: models.Model, diff: list[StoreFieldSpec]
    ) -> list[StoreFieldSpec]:
        extra = [
            Store.One("channel_id", [], as_thread=True),
            *self.env["discuss.channel.member"]._to_store_persona([]),
        ]
        if "message_unread_counter" in diff:
            extra.append(
                {
                    "message_unread_counter_bus_id": self.env["bus.bus"]
                    .sudo()
                    ._bus_last_id()
                }
            )
        return extra

    def _unlink_and_notify(self) -> None:
        for member in self:
            Store(bus_channel=member._bus_channel()).add(
                member.channel_id,
                {"close_chat_window": True, "isLocallyPinned": False},
            ).bus_send()
        members_by_channel = defaultdict(self.browse)
        for member in self:
            members_by_channel[member.channel_id] |= member
        self.unlink()
        for channel, members in members_by_channel.items():
            Store(bus_channel=channel).add(
                channel,
                [
                    Store.Many("channel_member_ids", [], mode="DELETE", value=members),
                    "member_count",
                ],
            ).bus_send()

    def unlink(self) -> Literal[True]:
        self.sudo().rtc_session_ids.unlink()
        domains = [
            [
                ("id", "not in", self.ids),
                ("partner_id", "=", member.partner_id.id),
                ("guest_id", "=", member.guest_id.id),
                ("channel_id", "in", member.channel_id.sub_channel_ids.ids),
            ]
            for member in self
        ]
        for member in self.env["discuss.channel.member"].search(Domain.OR(domains)):
            member.channel_id._action_unfollow(
                partner=member.partner_id, guest=member.guest_id
            )
        name_members_by_channel = {
            channel: channel.channel_name_member_ids for channel in self.channel_id
        }
        _debug.lifecycle(
            "unlink", members=self.ids, channels=len(name_members_by_channel)
        )
        res = super().unlink()
        for channel, members in name_members_by_channel.items():
            channel_sudo = channel.sudo()
            if channel_sudo.channel_name_member_ids != members:
                Store(bus_channel=channel).add(
                    channel_sudo,
                    Store.Many("channel_name_member_ids", sort="id"),
                ).bus_send()
        return res

    def _bus_channel(self) -> models.Model:
        return self.partner_id.main_user_id or self.guest_id

    @api.model
    def _member_email_domain(self, emails: Iterable[str]) -> Domain:
        return Domain.OR(
            [
                [(field, "=ilike", escape_like_wildcards(email))]
                for email in emails
                for field in ("guest_id.email", "partner_id.email")
            ]
        )

    def _notify_typing(self, is_typing: bool) -> None:
        for member in self:
            Store(bus_channel=member.channel_id).add(
                member,
                extra_fields={
                    "isTyping": is_typing,
                    "is_typing_dt": fields.Datetime.now(),
                },
            ).bus_send()

    def _notify_mute(self) -> None:
        for member in self:
            if member.mute_until_dt and member.mute_until_dt != datetime.max:  # noqa: DTZ901 - comparison against the 'muted forever' sentinel written by discuss_mute
                self.env.ref("mail.ir_cron_discuss_channel_member_unmute")._trigger(
                    member.mute_until_dt
                )

    @api.model
    def _cleanup_expired_mutes(self) -> None:
        members = self.search([("mute_until_dt", "<=", fields.Datetime.now())])
        members.write({"mute_until_dt": False})

    def _to_store_persona(
        self, field_specs: list[StoreFieldSpec] | None = None
    ) -> list:
        return [
            Store.Attr(
                "partner_id",
                lambda m: Store.One(
                    m.partner_id.sudo(),
                    (p_fields := m._get_store_partner_fields(field_specs)),
                    extra_fields=self.env["res.partner"]._get_fields_store_mention()
                    if p_fields or p_fields is None
                    else None,
                ),
                predicate=lambda m: m.partner_id,
            ),
            Store.Attr(
                "guest_id",
                lambda m: Store.One(
                    m.guest_id.sudo(), m._get_store_guest_fields(field_specs)
                ),
                predicate=lambda m: m.guest_id,
            ),
        ]

    def _to_store_defaults(self, target: Store.Target) -> StoreFieldsInput:
        return [
            Store.One("channel_id", [], as_thread=True),
            "create_date",
            "fetched_message_id",
            "last_seen_dt",
            "seen_message_id",
            *self.env["discuss.channel.member"]._to_store_persona(),
        ]

    def _get_store_partner_fields(
        self, field_specs: list[StoreFieldSpec]
    ) -> list[StoreFieldSpec]:
        self.check_singleton()
        return field_specs

    def _get_store_guest_fields(
        self, field_specs: list[StoreFieldSpec]
    ) -> list[StoreFieldSpec]:
        self.check_singleton()
        return field_specs

    def _rtc_join_call(
        self,
        store: Store | None = None,
        check_rtc_session_ids: list[int] | None = None,
        camera: bool = False,
    ) -> None:
        self.check_singleton()
        session_domain = []
        if self.partner_id:
            session_domain = [("partner_id", "=", self.partner_id.id)]
        elif self.guest_id:
            session_domain = [("guest_id", "=", self.guest_id.id)]
        user_sessions = self.search(session_domain).rtc_session_ids
        check_rtc_session_ids = (check_rtc_session_ids or []) + user_sessions.ids
        self.channel_id._rtc_cancel_invitations(member_ids=self.ids)
        user_sessions.unlink()
        rtc_session = self.env["discuss.channel.rtc.session"].create(
            {"channel_member_id": self.id, "is_camera_on": camera}
        )
        current_rtc_sessions, outdated_rtc_sessions = self._rtc_sync_sessions(
            check_rtc_session_ids=check_rtc_session_ids
        )
        _debug.lifecycle(
            "rtc_joined",
            member=self.id,
            channel=self.channel_id.id,
            session=rtc_session.id,
            previous_sessions=len(user_sessions),
            current=len(current_rtc_sessions),
            outdated=len(outdated_rtc_sessions),
            camera=camera,
        )
        ice_servers = self.env["mail.ice.server"]._get_ice_servers()
        self._join_sfu(ice_servers)
        if store:
            store.add(
                self.channel_id,
                {"rtc_session_ids": Store.Many(current_rtc_sessions, mode="ADD")},
            )
            store.add(
                self.channel_id,
                {
                    "rtc_session_ids": Store.Many(
                        outdated_rtc_sessions, [], mode="DELETE"
                    )
                },
            )
            store.add_singleton_values(
                "Rtc",
                {
                    "iceServers": ice_servers or False,
                    "localSession": Store.One(rtc_session),
                    "serverInfo": self._get_rtc_server_info(rtc_session, ice_servers),
                },
            )
        if self.channel_id._is_call_invitation_required():
            self._rtc_invite_members()

    def _join_sfu(self, ice_servers: list | None = None, force: bool = False) -> None:
        if len(self.channel_id.rtc_session_ids) < SFU_MODE_THRESHOLD and not force:
            if self.channel_id.sfu_channel_uuid:
                _debug.logic(
                    "sfu_released", channel=self.channel_id.id, reason="below_threshold"
                )
                self.channel_id.sfu_channel_uuid = None
                self.channel_id.sfu_server_url = None
            return
        elif self.channel_id.sfu_channel_uuid and self.channel_id.sfu_server_url:
            return
        sfu_server_url = discuss.get_sfu_url(self.env)
        if not sfu_server_url:
            _debug.logic("sfu_skipped", channel=self.channel_id.id, reason="no_url")
            return
        sfu_key = discuss.get_sfu_key(self.env)
        if not sfu_key:
            _debug.logic("sfu_skipped", channel=self.channel_id.id, reason="no_key")
            _logger.warning(
                "An SFU server URL is configured without an SFU key, user will stay in p2p"
            )
            return
        credentials = self.env["credential.credential"]
        sfu_local_key = credentials._get_system_secret("mail.sfu_local_key")
        if not sfu_local_key:
            if not credentials._is_encryption_key_configured():
                _debug.logic(
                    "sfu_skipped", channel=self.channel_id.id, reason="no_vault_key"
                )
                _logger.warning(
                    "An SFU server is configured but ODOO_API_ENCRYPTION_KEY is not "
                    "set, so no session signing key can be stored: user will stay in p2p"
                )
                return
            sfu_local_key = str(uuid.uuid4())
            credentials._set_system_secret("mail.sfu_local_key", sfu_local_key)
        json_web_token = jwt.sign(
            {
                "iss": f"{self.get_base_url()}:channel:{self.channel_id.id}",
                "key": sfu_local_key,
            },
            key=sfu_key,
            ttl=30,
            algorithm=jwt.Algorithm.HS256,
        )
        try:
            with _debug.perf("sfu_channel_requested", channel=self.channel_id.id):
                response = self.env["ir.egress"].request(
                    "GET",
                    sfu_server_url + "/v1/channel",
                    purpose="discuss_sfu",
                    policy="private",
                    headers={"Authorization": "jwt " + json_web_token},
                    timeout=3,
                )
                response.raise_for_status()
        except requests.exceptions.RequestException as error:
            _debug.logic(
                "sfu_skipped",
                channel=self.channel_id.id,
                reason="request_failed",
                error=type(error).__name__,
            )
            _logger.warning(
                "Failed to obtain a channel from the SFU server, user will stay in p2p: %s",
                error,
            )
            return
        response_dict = response.json()
        self.channel_id.sfu_channel_uuid = response_dict["uuid"]
        self.channel_id.sfu_server_url = response_dict["url"]
        _debug.lifecycle(
            "sfu_joined",
            channel=self.channel_id.id,
            sessions=len(self.channel_id.rtc_session_ids),
            forced=force,
        )
        for session in self.channel_id.rtc_session_ids:
            session._bus_send(
                "discuss.channel.rtc.session/sfu_hot_swap",
                {
                    "serverInfo": self._get_rtc_server_info(
                        session, ice_servers, key=sfu_local_key
                    )
                },
            )

    def _get_rtc_server_info(
        self,
        rtc_session: DiscussChannelRtcSession,
        ice_servers: list | None = None,
        key: str | None = None,
    ) -> dict | None:
        sfu_channel_uuid = self.channel_id.sfu_channel_uuid
        sfu_server_url = self.channel_id.sfu_server_url
        if not sfu_channel_uuid or not sfu_server_url:
            return None
        if not key:
            key = self.env["credential.credential"]._get_system_secret(
                "mail.sfu_local_key"
            )
        claims = {
            "session_id": rtc_session.id,
            "ice_servers": ice_servers,
        }
        json_web_token = jwt.sign(
            claims, key=key, ttl=60 * 60 * 8, algorithm=jwt.Algorithm.HS256
        )
        return {
            "url": sfu_server_url,
            "channelUUID": sfu_channel_uuid,
            "jsonWebToken": json_web_token,
        }

    def _rtc_leave_call(self, session_id: int | None = None) -> None:
        self.check_singleton()
        _debug.lifecycle(
            "rtc_left",
            member=self.id,
            channel=self.channel_id.id,
            session=session_id,
            sessions=len(self.rtc_session_ids),
        )
        if self.rtc_session_ids:
            if session_id:
                self.rtc_session_ids.filtered(lambda rec: rec.id == session_id).unlink()
                return
            self.rtc_session_ids.unlink()
        else:
            self.channel_id._rtc_cancel_invitations(member_ids=self.ids)

    def _rtc_sync_sessions(
        self, check_rtc_session_ids: list[int] | None = None
    ) -> tuple:
        self.check_singleton()
        self.channel_id.rtc_session_ids._remove_inactive_rtc_sessions()
        checked_ids = []
        for check_rtc_session_id in check_rtc_session_ids or []:
            try:
                checked_ids.append(int(check_rtc_session_id))
            except TypeError, ValueError:
                continue
        check_rtc_sessions = self.env["discuss.channel.rtc.session"].browse(checked_ids)
        return (
            self.channel_id.rtc_session_ids,
            check_rtc_sessions - self.channel_id.rtc_session_ids,
        )

    def _get_domain_rtc_invite_members(
        self, member_ids: list[int] | None = None
    ) -> Domain:
        self.check_singleton()
        domain = Domain.AND(
            [
                [("channel_id", "=", self.channel_id.id)],
                [("rtc_inviting_session_id", "=", False)],
                [("rtc_session_ids", "=", False)],
                Domain.OR(
                    [
                        [("partner_id", "=", False)],
                        [("partner_id.user_ids.manual_im_status", "!=", "busy")],
                    ]
                ),
                Domain("guest_id", "=", False)
                | Domain("guest_id.presence_ids.last_poll", ">", "-12H"),
            ]
        )
        if member_ids:
            domain &= Domain("id", "in", member_ids)
        return domain

    def _rtc_invite_members(self, member_ids: list[int] | None = None) -> Self:
        self.check_singleton()
        members = self.env["discuss.channel.member"].search(
            self._get_domain_rtc_invite_members(member_ids)
        )
        _debug.lifecycle(
            "rtc_invited",
            member=self.id,
            channel=self.channel_id.id,
            asked=len(member_ids or ()),
            invited=len(members),
        )
        if members:
            members.rtc_inviting_session_id = self.rtc_session_ids.id
            Store(bus_channel=self.channel_id).add(
                self.channel_id,
                {
                    "invited_member_ids": Store.Many(
                        members,
                        [
                            Store.One("channel_id", [], as_thread=True),
                            *self.env["discuss.channel.member"]._to_store_persona(
                                AVATAR_CARD_FIELDS
                            ),
                        ],
                        mode="ADD",
                    ),
                },
            ).bus_send()
            devices, private_key, public_key = (
                self.channel_id._web_push_get_partners_parameters(
                    members.partner_id.ids
                )
            )
            if devices:
                _debug.pipeline(
                    "rtc_invite_push", channel=self.channel_id.id, devices=len(devices)
                )
                icon = f"/web/image/discuss.channel/{self.channel_id.id}/avatar_128"
                if self.channel_id._channel_type_policy().push_icon_is_sender:
                    if guest := self.env["mail.guest"]._get_guest_from_context():
                        icon = f"/web/image/mail.guest/{guest.id}/avatar_128"
                    elif partner := self.env.user.partner_id:
                        icon = f"/web/image/res.partner/{partner.id}/avatar_128"
                languages = {partner.lang for partner in devices.partner_id}
                payload_by_lang = {}
                for lang in languages:
                    env_lang = self.with_context(lang=lang).env
                    payload_by_lang[lang] = {
                        "title": env_lang._("Incoming call"),
                        "options": {
                            "body": env_lang._(
                                "Conference: %s", self.channel_id.display_name
                            ),
                            "icon": icon,
                            "vibrate": [100, 50, 100],
                            "requireInteraction": True,
                            "tag": self.channel_id._get_call_notification_tag(),
                            "data": {
                                "type": PUSH_NOTIFICATION_TYPE.CALL,
                                "model": "discuss.channel",
                                "action": "mail.action_discuss",
                                "res_id": self.channel_id.id,
                            },
                            "actions": [
                                {
                                    "action": PUSH_NOTIFICATION_ACTION.DECLINE,
                                    "type": "button",
                                    "title": env_lang._("Decline"),
                                },
                                {
                                    "action": PUSH_NOTIFICATION_ACTION.ACCEPT,
                                    "type": "button",
                                    "title": env_lang._("Accept"),
                                },
                            ],
                        },
                    }
                self.channel_id._web_push_send_notification(
                    devices, private_key, public_key, payload_by_lang=payload_by_lang
                )
        return members

    def _mark_as_read(self, last_message_id: int) -> None:
        self.check_singleton()
        domain = [
            ("model", "=", "discuss.channel"),
            ("res_id", "=", self.channel_id.id),
            ("id", "<=", last_message_id),
        ]
        last_message = self.env["mail.message"].search(domain, order="id DESC", limit=1)
        if not last_message:
            return
        self._mark_message_read(last_message)

    def _mark_message_read(self, message: MailMessage, notify: bool = True) -> None:
        self.check_singleton()
        vals = {}
        seen_changed = self.seen_message_id.id < message.id
        if seen_changed:
            vals.update(
                {
                    "fetched_message_id": max(self.fetched_message_id.id, message.id),
                    "seen_message_id": message.id,
                    "last_seen_dt": fields.Datetime.now(),
                }
            )
        if self.new_message_separator != message.id + 1:
            vals["new_message_separator"] = message.id + 1
        _debug.lifecycle(
            "message_read",
            member=self.id,
            message=message.id,
            seen_changed=seen_changed,
            fields=list(vals),
            notify=notify,
        )
        if vals:
            self.write(vals)
        if not notify:
            return
        if seen_changed:
            self._notify_seen()
        elif not vals:
            self._notify_read_state()

    def _notify_seen(self) -> None:
        self.check_singleton()
        bus_channel = self._bus_channel()
        if self.channel_id.channel_type in self.channel_id._types_allowing_seen_infos():
            bus_channel = self.channel_id
        Store(bus_channel=bus_channel).add(
            self,
            [
                Store.One("channel_id", [], as_thread=True),
                *self.env["discuss.channel.member"]._to_store_persona(
                    AVATAR_CARD_FIELDS
                ),
                "seen_message_id",
            ],
        ).bus_send()

    def _notify_read_state(self) -> None:
        self.check_singleton()
        bus_last_id = self.env["bus.bus"].sudo()._bus_last_id()
        Store(bus_channel=self._bus_channel()).add(
            self,
            [
                Store.One("channel_id", [], as_thread=True),
                "message_unread_counter",
                {"message_unread_counter_bus_id": bus_last_id},
                "new_message_separator",
                "seen_message_id",
                *self.env["discuss.channel.member"]._to_store_persona([]),
            ],
        ).bus_send()

    def _update_new_message_separator(self, message_id: int) -> None:
        self.check_singleton()
        if message_id == self.new_message_separator:
            bus_last_id = self.env["bus.bus"].sudo()._bus_last_id()
            Store(bus_channel=self._bus_channel()).add(
                self,
                [
                    Store.One("channel_id", [], as_thread=True),
                    "message_unread_counter",
                    {"message_unread_counter_bus_id": bus_last_id},
                    "new_message_separator",
                    *self.env["discuss.channel.member"]._to_store_persona([]),
                ],
            ).bus_send()
            return
        self.new_message_separator = message_id

    def _notify_joined(self, invite_to_rtc_call: bool) -> None:
        channel_data = {}
        for member in self:
            channel = member.channel_id
            store = Store(bus_channel=member._bus_channel())
            key = (channel.id, store.target.is_current_user(self.env))
            if key not in channel_data:
                channel_data[key] = Store(bus_channel=member._bus_channel()).add(
                    channel
                )
            store.data = deepcopy(channel_data[key].data)
            store.add(member, "unpin_dt")
            payload = {
                "channel_id": channel.id,
                "invite_to_rtc_call": invite_to_rtc_call,
                "data": store.get_result(),
            }
            if not member.is_self and not self.env.user._is_public():
                payload["invited_by_user_id"] = self.env.user.id
            member._bus_send("discuss.channel/joined", payload)

    def _get_persona_name(self) -> str:
        return (self.partner_id.name if self.partner_id else self.guest_id.name) or ""

    def _get_html_link_title(self) -> str:
        return self._get_persona_name()

    def _format_html_link_list(self, extra_items: tuple = ()) -> Markup:
        params = [f"%(member_{member.id})s" for member in self] + list(extra_items)
        if not params:
            return Markup()
        return html_escape(format_list(self.env, params)) % {
            f"member_{member.id}": member._get_html_link(for_persona=True)
            for member in self
        }

    def _get_html_link(self, *args, for_persona: bool = False, **kwargs) -> Markup:
        if not for_persona:
            return super()._get_html_link(*args, **kwargs)
        if self.partner_id:
            return self.partner_id._get_html_link(
                title=f"@{self._get_html_link_title()}"
            )
        return Markup("<strong>%s</strong>") % self.guest_id.name
