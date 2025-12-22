# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
import uuid
from markupsafe import Markup
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.addons.mail.tools.discuss import Store
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from ...tools import jwt, discuss

_logger = logging.getLogger(__name__)
SFU_MODE_THRESHOLD = 3


class ChannelMember(models.Model):
    _name = "discuss.channel.member"
    _inherit = ["bus.listener.mixin"]
    _description = "Channel Member"
    _rec_names_search = ["channel_id", "partner_id", "guest_id"]
    _bypass_create_check = {}

    # identity
    partner_id = fields.Many2one("res.partner", "Partner", ondelete="cascade", index=True)
    guest_id = fields.Many2one("mail.guest", "Guest", ondelete="cascade", index=True)
    is_self = fields.Boolean(compute="_compute_is_self", search="_search_is_self")
    # channel
    channel_id = fields.Many2one("discuss.channel", "Channel", ondelete="cascade", required=True, auto_join=True)
    # state
    custom_channel_name = fields.Char('Custom channel name')
    fetched_message_id = fields.Many2one('mail.message', string='Last Fetched', index="btree_not_null")
    seen_message_id = fields.Many2one('mail.message', string='Last Seen', index="btree_not_null")
    new_message_separator = fields.Integer(help="Message id before which the separator should be displayed", default=0, required=True)
    message_unread_counter = fields.Integer('Unread Messages Counter', compute='_compute_message_unread', compute_sudo=True)
    fold_state = fields.Selection([('open', 'Open'), ('folded', 'Folded'), ('closed', 'Closed')], string='Conversation Fold State', default='closed')
    custom_notifications = fields.Selection(
        [("all", "All Messages"), ("mentions", "Mentions Only"), ("no_notif", "Nothing")],
        "Customized Notifications",
        help="Use default from user settings if not specified. This setting will only be applied to channels.",
    )
    mute_until_dt = fields.Datetime("Mute notifications until", help="If set, the member will not receive notifications from the channel until this date.")
    is_pinned = fields.Boolean("Is pinned on the interface", compute="_compute_is_pinned", search="_search_is_pinned")
    unpin_dt = fields.Datetime("Unpin date", index=True, help="Contains the date and time when the channel was unpinned by the user.")
    last_interest_dt = fields.Datetime("Last Interest", index=True, default=fields.Datetime.now, help="Contains the date and time of the last interesting event that happened in this channel for this user. This includes: creating, joining, pinning")
    last_seen_dt = fields.Datetime("Last seen date")
    # RTC
    rtc_session_ids = fields.One2many(string="RTC Sessions", comodel_name='discuss.channel.rtc.session', inverse_name='channel_member_id')
    rtc_inviting_session_id = fields.Many2one('discuss.channel.rtc.session', string='Ringing session')

    @api.autovacuum
    def _gc_unpin_outdated_sub_channels(self):
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
             WHERE (
                       member.unpin_dt IS NULL
                    OR member.last_interest_dt >= member.unpin_dt
                    OR channel.last_interest_dt >= member.unpin_dt
               )
               AND COALESCE(member.last_interest_dt, member.create_date) < %(outdated_dt)s
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
            [("id", "in", [row[0] for row in self.env.cr.fetchall()])],
        )
        members.unpin_dt = fields.Datetime.now()
        for member in members:
            member._bus_send("discuss.channel/unpin", {"id": member.channel_id.id})

    @api.constrains('partner_id')
    def _contrains_no_public_member(self):
        for member in self:
            if any(user._is_public() for user in member.partner_id.user_ids):
                raise ValidationError(_("Channel members cannot include public users."))

    @api.depends_context("uid", "guest")
    def _compute_is_self(self):
        if not self:
            return
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        self.is_self = False
        for member in self:
            if current_partner and member.partner_id == current_partner:
                member.is_self = True
            if current_guest and member.guest_id == current_guest:
                member.is_self = True

    def _search_is_self(self, operator, operand):
        is_in = (operator == "=" and operand) or (operator == "!=" and not operand)
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        if is_in:
            return [
                '|',
                ("partner_id", "=", current_partner.id) if current_partner else expression.FALSE_LEAF,
                ("guest_id", "=", current_guest.id) if current_guest else expression.FALSE_LEAF,
            ]
        else:
            return [
                ("partner_id", "!=", current_partner.id) if current_partner else expression.TRUE_LEAF,
                ("guest_id", "!=", current_guest.id) if current_guest else expression.TRUE_LEAF,
            ]

    def _search_is_pinned(self, operator, operand):
        if (operator == "=" and operand) or (operator == "!=" and not operand):
            return expression.OR([
                [("unpin_dt", "=", False)],
                [("last_interest_dt", ">=", self._field_to_sql(self._table, "unpin_dt"))],
                [("channel_id.last_interest_dt", ">=", self._field_to_sql(self._table, "unpin_dt"))],
            ])
        else:
            return [
                ("unpin_dt", "!=", False),
                ("last_interest_dt", "<", self._field_to_sql(self._table, "unpin_dt")),
                ("channel_id.last_interest_dt", "<", self._field_to_sql(self._table, "unpin_dt")),
            ]

    @api.depends("channel_id.message_ids", "new_message_separator")
    def _compute_message_unread(self):
        if self.ids:
            self.env['mail.message'].flush_model()
            self.flush_recordset(['channel_id', 'new_message_separator'])
            self.env.cr.execute("""
                     SELECT count(mail_message.id) AS count,
                            discuss_channel_member.id
                       FROM mail_message
                 INNER JOIN discuss_channel_member
                         ON discuss_channel_member.channel_id = mail_message.res_id
                      WHERE mail_message.model = 'discuss.channel'
                        AND mail_message.message_type NOT IN ('notification', 'user_notification')
                        AND mail_message.id >= discuss_channel_member.new_message_separator
                        AND discuss_channel_member.id IN %(ids)s
                   GROUP BY discuss_channel_member.id
            """, {'ids': tuple(self.ids)})
            unread_counter_by_member = {res['id']: res['count'] for res in self.env.cr.dictfetchall()}
            for member in self:
                member.message_unread_counter = unread_counter_by_member.get(member.id)
        else:
            self.message_unread_counter = 0

    @api.depends("partner_id.name", "guest_id.name", "channel_id.display_name")
    def _compute_display_name(self):
        for member in self:
            member.display_name = _(
                "“%(member_name)s” in “%(channel_name)s”",
                member_name=member.partner_id.name or member.guest_id.name,
                channel_name=member.channel_id.display_name,
            )

    @api.depends("last_interest_dt", "unpin_dt", "channel_id.last_interest_dt")
    def _compute_is_pinned(self):
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

    def init(self):
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS discuss_channel_member_partner_unique ON %s (channel_id, partner_id) WHERE partner_id IS NOT NULL" % self._table)
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS discuss_channel_member_guest_unique ON %s (channel_id, guest_id) WHERE guest_id IS NOT NULL" % self._table)

    _sql_constraints = [
        ("partner_or_guest_exists", "CHECK((partner_id IS NOT NULL AND guest_id IS NULL) OR (partner_id IS NULL AND guest_id IS NOT NULL))", "A channel member must be a partner or a guest."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("mail_create_bypass_create_check") is self._bypass_create_check:
            self = self.sudo()
        for vals in vals_list:
            if "channel_id" not in vals:
                raise UserError(
                    _(
                        "It appears you're trying to create a channel member, but it seems like you forgot to specify the related channel. "
                        "To move forward, please make sure to provide the necessary channel information."
                    )
                )
            channel = self.env["discuss.channel"].browse(vals["channel_id"])
            if channel.channel_type == "chat" and len(channel.channel_member_ids) > 0:
                raise UserError(
                    _("Adding more members to this chat isn't possible; it's designed for just two people.")
                )
        res = super().create(vals_list)
        # help the ORM to detect changes
        res.partner_id.invalidate_recordset(["channel_ids"])
        res.guest_id.invalidate_recordset(["channel_ids"])
        # Always link members to parent channels as well. Member list should be
        # kept in sync.
        for member in res:
            if parent := member.channel_id.parent_channel_id:
                parent.add_members(partner_ids=member.partner_id.ids, guest_ids=member.guest_id.ids)
        return res

    def write(self, vals):
        for channel_member in self:
            for field_name in ['channel_id', 'partner_id', 'guest_id']:
                if field_name in vals and vals[field_name] != channel_member[field_name].id:
                    raise AccessError(_('You can not write on %(field_name)s.', field_name=field_name))
        return super().write(vals)

    def unlink(self):
        # sudo: discuss.channel.rtc.session - cascade unlink of sessions for self member
        self.sudo().rtc_session_ids.unlink()  # ensure unlink overrides are applied
        # always unlink members of sub-channels as well
        domains = [
            [
                ("partner_id", "=", member.partner_id.id),
                ("guest_id", "=", member.guest_id.id),
                ("channel_id", "in", member.channel_id.sub_channel_ids.ids),
            ]
            for member in self
        ]
        for member in self.env["discuss.channel.member"].search(expression.OR(domains)):
            member.channel_id._action_unfollow(partner=member.partner_id, guest=member.guest_id)
        return super().unlink()

    def _bus_channel(self):
        return (self.partner_id or self.guest_id)._bus_channel()

    def _notify_typing(self, is_typing):
        """ Broadcast the typing notification to channel members
            :param is_typing: (boolean) tells whether the members are typing or not
        """
        for member in self:
            member.channel_id._bus_send_store(Store(member).add(member, {"isTyping": is_typing, "is_typing_dt": fields.Datetime.now()}))

    def _notify_mute(self):
        for member in self:
            member._bus_send_store(member.channel_id, {"mute_until_dt": member.mute_until_dt})
            if member.mute_until_dt and member.mute_until_dt != -1:
                self.env.ref("mail.ir_cron_discuss_channel_member_unmute")._trigger(member.mute_until_dt)

    def set_custom_notifications(self, custom_notifications):
        self.ensure_one()
        self.custom_notifications = custom_notifications
        self._bus_send_store(self.channel_id, {"custom_notifications": self.custom_notifications})

    @api.model
    def _cleanup_expired_mutes(self):
        """
        Cron job for cleanup expired unmute by resetting mute_until_dt and sending bus notifications.
        """
        members = self.search([("mute_until_dt", "<=", fields.Datetime.now())])
        members.write({"mute_until_dt": False})
        members._notify_mute()

    def _to_store(self, store: Store, /, *, fields=None, extra_fields=None):
        if fields is None:
            fields = {
                "channel": [],
                "create_date": True,
                "fetched_message_id": True,
                "persona": None,
                "seen_message_id": True,
                "last_seen_dt": True,
            }
        if extra_fields:
            fields.update(extra_fields)
        bus_last_id = fields.pop("message_unread_counter_bus_id", None)
        if "message_unread_counter" in fields and bus_last_id is None:
            # sudo: bus.bus: reading non-sensitive last id
            bus_last_id = self.env["bus.bus"].sudo()._bus_last_id()
        for member in self:
            data = member._read_format(
                [
                    field
                    for field in fields
                    if field not in ["channel", "fetched_message_id", "seen_message_id", "persona"]
                ],
                load=False,
            )[0]
            if "channel" in fields:
                data["thread"] = Store.one(member.channel_id, as_thread=True, only_id=True)
            if "persona" in fields:
                if member.partner_id:
                    # sudo: res.partner - reading partner related to a member is considered acceptable
                    data["persona"] = Store.one(
                        member.partner_id.sudo(),
                        fields=member._get_store_partner_fields(fields["persona"]),
                    )
                if member.guest_id:
                    # sudo: mail.guest - reading guest related to a member is considered acceptable
                    data["persona"] = Store.one(member.guest_id.sudo(), fields=fields["persona"])
            if "fetched_message_id" in fields:
                data["fetched_message_id"] = Store.one(member.fetched_message_id, only_id=True)
            if "seen_message_id" in fields:
                data["seen_message_id"] = Store.one(member.seen_message_id, only_id=True)
            if "message_unread_counter" in fields:
                data["message_unread_counter_bus_id"] = bus_last_id
            store.add(member, data)

    def _get_store_partner_fields(self, fields):
        self.ensure_one()
        return fields

    def _channel_fold(self, state, state_count):
        """Update the fold_state of the given member. The change will be
        broadcasted to the member channel.

        :param state: the new status of the session for the current member.
        """
        self.ensure_one()
        if self.fold_state == state:
            return
        self.fold_state = state
        self._bus_send(
            "discuss.Thread/fold_state",
            {
                "fold_state": self.fold_state,
                "foldStateCount": state_count,
                "id": self.channel_id.id,
                "model": "discuss.channel",
            },
        )
    # --------------------------------------------------------------------------
    # RTC (voice/video)
    # --------------------------------------------------------------------------

    def _rtc_join_call(self, store=None, check_rtc_session_ids=None, camera=False):
        self.ensure_one()
        check_rtc_session_ids = (check_rtc_session_ids or []) + self.rtc_session_ids.ids
        self.channel_id._rtc_cancel_invitations(member_ids=self.ids)
        self.rtc_session_ids.unlink()
        rtc_session = self.env['discuss.channel.rtc.session'].create({'channel_member_id': self.id, 'is_camera_on': camera})
        current_rtc_sessions, outdated_rtc_sessions = self._rtc_sync_sessions(check_rtc_session_ids=check_rtc_session_ids)
        ice_servers = self.env["mail.ice.server"]._get_ice_servers()
        self._join_sfu(ice_servers)
        if store:
            store.add(self.channel_id, {"rtcSessions": Store.many(current_rtc_sessions, "ADD")})
            store.add(
                self.channel_id,
                {"rtcSessions": Store.many(outdated_rtc_sessions, "DELETE", only_id=True)},
            )
            store.add(
                "Rtc",
                {
                    "iceServers": ice_servers or False,
                    "selfSession": Store.one(rtc_session),
                    "serverInfo": self._get_rtc_server_info(rtc_session, ice_servers),
                },
            )
        if len(self.channel_id.rtc_session_ids) == 1 and self.channel_id.channel_type != "channel":
            self.channel_id.message_post(body=_("%s started a live conference", self.partner_id.name or self.guest_id.name), message_type='notification')
            self._rtc_invite_members()

    def _join_sfu(self, ice_servers=None, force=False):
        if len(self.channel_id.rtc_session_ids) < SFU_MODE_THRESHOLD and not force:
            if self.channel_id.sfu_channel_uuid:
                self.channel_id.sfu_channel_uuid = None
                self.channel_id.sfu_server_url = None
            return
        elif self.channel_id.sfu_channel_uuid and self.channel_id.sfu_server_url:
            return
        sfu_server_url = discuss.get_sfu_url(self.env)
        if not sfu_server_url:
            return
        sfu_local_key = self.env["ir.config_parameter"].sudo().get_param("mail.sfu_local_key")
        if not sfu_local_key:
            sfu_local_key = str(uuid.uuid4())
            self.env["ir.config_parameter"].sudo().set_param("mail.sfu_local_key", sfu_local_key)
        json_web_token = jwt.sign(
            {"iss": f"{self.get_base_url()}:channel:{self.channel_id.id}", "key": sfu_local_key},
            key=discuss.get_sfu_key(self.env),
            ttl=30,
            algorithm=jwt.Algorithm.HS256,
        )
        try:
            response = requests.get(
                sfu_server_url + "/v1/channel",
                headers={"Authorization": "jwt " + json_web_token},
                timeout=3,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            _logger.warning("Failed to obtain a channel from the SFU server, user will stay in p2p: %s", error)
            return
        response_dict = response.json()
        self.channel_id.sfu_channel_uuid = response_dict["uuid"]
        self.channel_id.sfu_server_url = response_dict["url"]
        for session in self.channel_id.rtc_session_ids:
            session._bus_send(
                "discuss.channel.rtc.session/sfu_hot_swap",
                {"serverInfo": self._get_rtc_server_info(session, ice_servers, key=sfu_local_key)},
            )

    def _get_rtc_server_info(self, rtc_session, ice_servers=None, key=None):
        sfu_channel_uuid = self.channel_id.sfu_channel_uuid
        sfu_server_url = self.channel_id.sfu_server_url
        if not sfu_channel_uuid or not sfu_server_url:
            return None
        if not key:
            key = self.env["ir.config_parameter"].sudo().get_param("mail.sfu_local_key")
        claims = {
            "session_id": rtc_session.id,
            "ice_servers": ice_servers,
        }
        json_web_token = jwt.sign(claims, key=key, ttl=60 * 60 * 8, algorithm=jwt.Algorithm.HS256)  # 8 hours
        return {"url": sfu_server_url, "channelUUID": sfu_channel_uuid, "jsonWebToken": json_web_token}

    def _rtc_leave_call(self):
        self.ensure_one()
        if self.rtc_session_ids:
            self.rtc_session_ids.unlink()
        else:
            self.channel_id._rtc_cancel_invitations(member_ids=self.ids)

    def _rtc_sync_sessions(self, check_rtc_session_ids=None):
        """Synchronize the RTC sessions for self channel member.
            - Inactive sessions of the channel are deleted.
            - Current sessions are returned.
            - Sessions given in check_rtc_session_ids that no longer exists
              are returned as non-existing.
            :param list check_rtc_session_ids: list of the ids of the sessions to check
            :returns tuple: (current_rtc_sessions, outdated_rtc_sessions)
        """
        self.ensure_one()
        self.channel_id.rtc_session_ids._delete_inactive_rtc_sessions()
        check_rtc_sessions = self.env['discuss.channel.rtc.session'].browse([int(check_rtc_session_id) for check_rtc_session_id in (check_rtc_session_ids or [])])
        return self.channel_id.rtc_session_ids, check_rtc_sessions - self.channel_id.rtc_session_ids

    def _get_rtc_invite_members_domain(self, member_ids=None):
        """ Get the domain used to get the members to invite to and RTC call on
        the member's channel.

        :param list member_ids: List of the partner ids to invite.
        """
        self.ensure_one()
        recent_guest_ids = self.env["bus.presence"].sudo().search([
            ("guest_id", "in", self.channel_id.channel_member_ids.guest_id.ids),
            ("last_poll", ">", fields.Datetime.now() - timedelta(hours=12))
        ]).guest_id
        domain = [
            ('channel_id', '=', self.channel_id.id),
            ('rtc_inviting_session_id', '=', False),
            ('rtc_session_ids', '=', False),
            "|", ("guest_id", "=", False), ("guest_id", "in", recent_guest_ids.ids),
        ]
        if member_ids:
            domain = expression.AND([domain, [('id', 'in', member_ids)]])
        return domain

    def _rtc_invite_members(self, member_ids=None):
        """ Sends invitations to join the RTC call to all connected members of the thread who are not already invited,
            if member_ids is set, only the specified ids will be invited.

            :param list member_ids: list of the partner ids to invite
        """
        self.ensure_one()
        members = self.env["discuss.channel.member"].search(
            self._get_rtc_invite_members_domain(member_ids)
        )
        for member in members:
            member.rtc_inviting_session_id = self.rtc_session_ids.id
            member._bus_send_store(
                self.channel_id, {"rtcInvitingSession": Store.one(member.rtc_inviting_session_id, extra=True)}
            )
        if members:
            self.channel_id._bus_send_store(
                self.channel_id,
                {
                    "invitedMembers": Store.many(
                        members, "ADD", fields={"channel": [], "persona": ["name", "im_status"]}
                    ),
                },
            )
        return members

    def _mark_as_read(self, last_message_id, sync=False):
        """
        Mark channel as read by updating the seen message id of the current
        member as well as its new message separator.

        :param last_message_id: the id of the message to be marked as read.
        :param sync: wether the new message separator and the unread counter in
            the UX will sync to their server values.
        """
        self.ensure_one()
        domain = [
            ("model", "=", "discuss.channel"),
            ("res_id", "=", self.channel_id.id),
            ("id", "<=", last_message_id),
        ]
        last_message = self.env['mail.message'].search(domain, order="id DESC", limit=1)
        if not last_message:
            return
        self._set_last_seen_message(last_message)
        self._set_new_message_separator(last_message.id + 1, sync=sync)

    def _set_last_seen_message(self, message, notify=True):
        """
        Set the last seen message of the current member.

        :param message: the message to set as last seen message.
        :param notify: whether to send a bus notification relative to the new
            last seen message.
        """
        self.ensure_one()
        target = self
        if self.seen_message_id.id < message.id:
            self.fetched_message_id = max(self.fetched_message_id.id, message.id)
            self.seen_message_id = message.id
            self.last_seen_dt = fields.Datetime.now()
            if self.channel_id.channel_type in self.channel_id._types_allowing_seen_infos():
                target = self.channel_id
        if not notify:
            return
        target._bus_send_store(
            self, fields={"channel": [], "persona": ["name"], "seen_message_id": True}
        )

    def _set_new_message_separator(self, message_id, sync=False):
        """
        :param message_id: id of the message above which the new message
            separator should be displayed.
        :param sync: whether the new message separator and the unread counter
            in the UX will sync to their server values.

        """
        self.ensure_one()
        if message_id != self.new_message_separator:
            self.new_message_separator = message_id
        self._bus_send_store(
            Store(
                self,
                fields={
                    "channel": [],
                    "message_unread_counter": True,
                    "new_message_separator": True,
                    "persona": ["name"],
                },
            ).add(self, {"syncUnread": sync})
        )

    def _get_html_link(self, *args, for_persona=False, **kwargs):
        if not for_persona:
            return self._get_html_link(*args, **kwargs)
        if self.partner_id:
            return self.partner_id._get_html_link(title=f"@{self.partner_id.name}")
        return Markup("<strong>%s</strong>") % self.guest_id.name
