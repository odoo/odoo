# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
import uuid
from datetime import timedelta
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.web_push import PUSH_NOTIFICATION_ACTION, PUSH_NOTIFICATION_TYPE
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import SQL

from ...tools import jwt, discuss

_logger = logging.getLogger(__name__)
SFU_MODE_THRESHOLD = 3


class DiscussChannelMember(models.Model):
    _name = 'discuss.channel.member'
    _inherit = ["bus.listener.mixin"]
    _description = "Channel Member"
    _rec_names_search = ["channel_id", "partner_id", "guest_id"]
    _bypass_create_check = {}

    # identity
    partner_id = fields.Many2one("res.partner", "Partner", ondelete="cascade", index=True)
    guest_id = fields.Many2one("mail.guest", "Guest", ondelete="cascade", index=True)
    is_self = fields.Boolean(compute="_compute_is_self", search="_search_is_self")
    # channel
    channel_id = fields.Many2one("discuss.channel", "Channel", ondelete="cascade", required=True, bypass_search_access=True)
    # state
    custom_channel_name = fields.Char('Custom channel name')
    fetched_message_id = fields.Many2one('mail.message', string='Last Fetched', index="btree_not_null")
    seen_message_id = fields.Many2one('mail.message', string='Last Seen', index="btree_not_null")
    new_message_separator = fields.Integer(help="Message id before which the separator should be displayed", default=0, required=True)
    message_unread_counter = fields.Integer('Unread Messages Counter', compute='_compute_message_unread', compute_sudo=True)
    custom_notifications = fields.Selection(
        [("all", "All Messages"), ("mentions", "Mentions Only"), ("no_notif", "Nothing")],
        "Customized Notifications",
        help="Use default from user settings if not specified. This setting will only be applied to channels.",
    )
    mute_until_dt = fields.Datetime("Mute notifications until", help="If set, the member will not receive notifications from the channel until this date.")
    is_pinned = fields.Boolean("Is pinned on the interface", compute="_compute_is_pinned", search="_search_is_pinned")
    unpin_dt = fields.Datetime("Unpin date", index=True, help="Contains the date and time when the channel was unpinned by the user.")
    last_interest_dt = fields.Datetime(
        "Last Interest",
        default=lambda self: fields.Datetime.now() - timedelta(seconds=1),
        index=True,
        help="Contains the date and time of the last interesting event that happened in this channel for this user. This includes: creating, joining, pinning",
    )
    last_seen_dt = fields.Datetime("Last seen date")
    # RTC
    rtc_session_ids = fields.One2many(string="RTC Sessions", comodel_name='discuss.channel.rtc.session', inverse_name='channel_member_id')
    rtc_inviting_session_id = fields.Many2one('discuss.channel.rtc.session', string='Ringing session')

    _seen_message_id_idx = models.Index("(channel_id, partner_id, seen_message_id)")

    @api.autovacuum
    def _gc_unpin_outdated_sub_channels(self):
        outdated_dt = fields.Datetime.now() - timedelta(days=2)
        domain = Domain.AND(
            [
                [
                    ("channel_id.parent_channel_id", "!=", False),
                    ("last_interest_dt", "<", outdated_dt),
                ],
                Domain.OR(
                    [
                        [("channel_id.last_interest_dt", "=", False)],
                        [("channel_id.last_interest_dt", "<", outdated_dt)],
                    ]
                ),
            ]
        )
        members = self.env["discuss.channel.member"].search(domain)
        members.unpin_dt = fields.Datetime.now()
        for member in members:
            Store(bus_channel=member._bus_channel()).add(
                member.channel_id,
                {"close_chat_window": True, "is_pinned": False},
            ).bus_send()

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
        if operator != 'in':
            return NotImplemented
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        domain_partner = Domain("partner_id", "=", current_partner.id) if current_partner else Domain.FALSE
        domain_guest = Domain("guest_id", "=", current_guest.id) if current_guest else Domain.FALSE
        return domain_partner | domain_guest

    def _search_is_pinned(self, operator, operand):
        if operator != 'in':
            return NotImplemented

        def custom_pinned(model: models.BaseModel, alias, query):
            channel_model = model.browse().channel_id
            channel_alias = query.make_alias(alias, 'channel_id')
            query.add_join("LEFT JOIN", channel_alias, channel_model._table, SQL(
                "%s = %s",
                model._field_to_sql(alias, 'channel_id'),
                channel_model._field_to_sql(channel_alias, 'id'),
            ))
            return SQL(
                """(%(unpin)s IS NULL
                    OR %(last_interest)s >= %(unpin)s
                    OR %(channel_last_interest)s >= %(unpin)s
                )""",
                unpin=model._field_to_sql(alias, "unpin_dt", query),
                last_interest=model._field_to_sql(alias, "last_interest_dt", query),
                channel_last_interest=channel_model._field_to_sql(channel_alias, "last_interest_dt", query),
            )

        return Domain.custom(to_sql=custom_pinned)

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

    _partner_unique = models.UniqueIndex("(channel_id, partner_id) WHERE partner_id IS NOT NULL")
    _guest_unique = models.UniqueIndex("(channel_id, guest_id) WHERE guest_id IS NOT NULL")
    _partner_or_guest_exists = models.Constraint(
        'CHECK((partner_id IS NOT NULL AND guest_id IS NULL) OR (partner_id IS NULL AND guest_id IS NOT NULL))',
        'A channel member must be a partner or a guest.',
    )

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
                parent._add_members(partners=member.partner_id, guests=member.guest_id)
        return res

    def write(self, vals):
        for channel_member in self:
            for field_name in ['channel_id', 'partner_id', 'guest_id']:
                if field_name in vals and vals[field_name] != channel_member[field_name].id:
                    raise AccessError(_('You can not write on %(field_name)s.', field_name=field_name))

        def get_field_name(field_description):
            if isinstance(field_description, Store.Attr):
                return field_description.field_name
            return field_description

        def get_vals(member):
            return {
                get_field_name(field_description): (
                    member[get_field_name(field_description)],
                    field_description,
                )
                for field_description in self._sync_field_names()
            }

        old_vals_by_member = {member: get_vals(member) for member in self}
        result = super().write(vals)
        for member in self:
            new_values = get_vals(member)
            diff = []
            for field_name, (new_value, field_description) in new_values.items():
                old_value = old_vals_by_member[member][field_name][0]
                if new_value != old_value:
                    diff.append(field_description)
            if diff:
                diff.extend(
                    [
                        Store.One("channel_id", [], as_thread=True),
                        *self.env["discuss.channel.member"]._to_store_persona([]),
                    ]
                )
                if "message_unread_counter" in diff:
                    # sudo: bus.bus: reading non-sensitive last id
                    bus_last_id = self.env["bus.bus"].sudo()._bus_last_id()
                    diff.append({"message_unread_counter_bus_id": bus_last_id})
                Store(bus_channel=member._bus_channel()).add(member, diff).bus_send()
        return result

    @api.model
    def _sync_field_names(self):
        return [
            "custom_channel_name",
            "custom_notifications",
            "last_interest_dt",
            "message_unread_counter",
            "mute_until_dt",
            "new_message_separator",
            # sudo: discuss.channel.rtc.session - each member can see who is inviting them
            Store.One(
                "rtc_inviting_session_id",
                extra_fields=self.rtc_inviting_session_id._get_store_extra_fields(),
                sudo=True,
            ),
            "unpin_dt",
        ]

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
        for member in self.env["discuss.channel.member"].search(Domain.OR(domains)):
            member.channel_id._action_unfollow(partner=member.partner_id, guest=member.guest_id)
        return super().unlink()

    def _bus_channel(self):
        return self.partner_id.main_user_id or self.guest_id

    def _notify_typing(self, is_typing):
        """ Broadcast the typing notification to channel members
            :param is_typing: (boolean) tells whether the members are typing or not
        """
        for member in self:
            Store(bus_channel=member.channel_id).add(
                member,
                extra_fields={"isTyping": is_typing, "is_typing_dt": fields.Datetime.now()},
            ).bus_send()

    def _notify_mute(self):
        for member in self:
            if member.mute_until_dt and member.mute_until_dt != -1:
                self.env.ref("mail.ir_cron_discuss_channel_member_unmute")._trigger(member.mute_until_dt)

    @api.model
    def _cleanup_expired_mutes(self):
        """
        Cron job for cleanup expired unmute by resetting mute_until_dt and sending bus notifications.
        """
        members = self.search([("mute_until_dt", "<=", fields.Datetime.now())])
        members.write({"mute_until_dt": False})
        members._notify_mute()

    def _to_store_persona(self, fields=None):
        if fields == "avatar_card":
            fields = ["avatar_128", "im_status", "name"]
        return [
            # sudo: res.partner - reading partner related to a member is considered acceptable
            Store.Attr(
                "partner_id",
                lambda m: Store.One(m.partner_id.sudo(), m._get_store_partner_fields(fields)),
                predicate=lambda m: m.partner_id,
            ),
            # sudo: mail.guest - reading guest related to a member is considered acceptable
            Store.Attr(
                "guest_id",
                lambda m: Store.One(m.guest_id.sudo(), m._get_store_guest_fields(fields)),
                predicate=lambda m: m.guest_id,
            ),
        ]

    def _to_store_defaults(self, target):
        return [
            Store.One("channel_id", [], as_thread=True),
            "create_date",
            "fetched_message_id",
            "last_seen_dt",
            "seen_message_id",
            *self.env["discuss.channel.member"]._to_store_persona(),
        ]

    def _get_store_partner_fields(self, fields):
        self.ensure_one()
        return fields

    def _get_store_guest_fields(self, fields):
        self.ensure_one()
        return fields

    # --------------------------------------------------------------------------
    # RTC (voice/video)
    # --------------------------------------------------------------------------

    def _rtc_join_call(self, store: Store = None, check_rtc_session_ids=None, camera=False):
        self.ensure_one()
        session_domain = []
        if self.partner_id:
            session_domain = [("partner_id", "=", self.partner_id.id)]
        elif self.guest_id:
            session_domain = [("guest_id", "=", self.guest_id.id)]
        user_sessions = self.search(session_domain).rtc_session_ids
        check_rtc_session_ids = (check_rtc_session_ids or []) + user_sessions.ids
        self.channel_id._rtc_cancel_invitations(member_ids=self.ids)
        user_sessions.unlink()
        rtc_session = self.env['discuss.channel.rtc.session'].create({'channel_member_id': self.id, 'is_camera_on': camera})
        current_rtc_sessions, outdated_rtc_sessions = self._rtc_sync_sessions(check_rtc_session_ids=check_rtc_session_ids)
        ice_servers = self.env["mail.ice.server"]._get_ice_servers()
        self._join_sfu(ice_servers)
        if store:
            store.add(
                self.channel_id, {"rtc_session_ids": Store.Many(current_rtc_sessions, mode="ADD")}
            )
            store.add(
                self.channel_id,
                {"rtc_session_ids": Store.Many(outdated_rtc_sessions, [], mode="DELETE")},
            )
            store.add_singleton_values(
                "Rtc",
                {
                    "iceServers": ice_servers or False,
                    "localSession": Store.One(rtc_session),
                    "serverInfo": self._get_rtc_server_info(rtc_session, ice_servers),
                },
            )
        if self.channel_id._should_invite_members_to_join_call():
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

    def _rtc_leave_call(self, session_id=None):
        self.ensure_one()
        if self.rtc_session_ids:
            if session_id:
                self.rtc_session_ids.filtered(lambda rec: rec.id == session_id).unlink()
                return
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
            :returns: (current_rtc_sessions, outdated_rtc_sessions)
            :rtype: tuple
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
        domain = Domain.AND([
            [('channel_id', '=', self.channel_id.id)],
            [('rtc_inviting_session_id', '=', False)],
            [('rtc_session_ids', '=', False)],
            Domain.OR([
                [("partner_id", "=", False)],
                [("partner_id.user_ids.manual_im_status", "!=", "busy")],
            ]),
        ])
        if member_ids:
            domain &= Domain('id', 'in', member_ids)
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
        if members:
            members.rtc_inviting_session_id = self.rtc_session_ids.id
            Store(bus_channel=self.channel_id).add(
                self.channel_id,
                {
                    "invited_member_ids": Store.Many(
                        members,
                        [
                            Store.One("channel_id", [], as_thread=True),
                            *self.env["discuss.channel.member"]._to_store_persona("avatar_card"),
                        ],
                        mode="ADD",
                    ),
                },
            ).bus_send()
            devices, private_key, public_key = self.channel_id._web_push_get_partners_parameters(members.partner_id.ids)
            if devices:
                if self.channel_id.channel_type != 'chat':
                    icon = f"/web/image/discuss.channel/{self.channel_id.id}/avatar_128"
                elif guest := self.env["mail.guest"]._get_guest_from_context():
                    icon = f"/web/image/mail.guest/{guest.id}/avatar_128"
                elif partner := self.env.user.partner_id:
                    icon = f"/web/image/res.partner/{partner.id}/avatar_128"
                languages = [partner.lang for partner in devices.partner_id]
                payload_by_lang = {}
                for lang in languages:
                    env_lang = self.with_context(lang=lang).env
                    payload_by_lang[lang] = {
                        "title": env_lang._("Incoming call"),
                        "options": {
                            "body": env_lang._("Conference: %s", self.channel_id.display_name),
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
                            ]
                        }
                    }
                self.channel_id._web_push_send_notification(devices, private_key, public_key, payload_by_lang=payload_by_lang)
        return members

    def _mark_as_read(self, last_message_id):
        """
        Mark channel as read by updating the seen message id of the current
        member as well as its new message separator.

        :param last_message_id: the id of the message to be marked as read.
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
        self._set_new_message_separator(last_message.id + 1)

    def _set_last_seen_message(self, message, notify=True):
        """
        Set the last seen message of the current member.

        :param message: the message to set as last seen message.
        :param notify: whether to send a bus notification relative to the new
            last seen message.
        """
        self.ensure_one()
        if self.seen_message_id.id >= message.id:
            return
        self.fetched_message_id = max(self.fetched_message_id.id, message.id)
        self.seen_message_id = message.id
        self.last_seen_dt = fields.Datetime.now()
        if not notify:
            return
        bus_channel = self._bus_channel()
        if self.channel_id.channel_type in self.channel_id._types_allowing_seen_infos():
            bus_channel = self.channel_id
        Store(bus_channel=bus_channel).add(
            self,
            [
                Store.One("channel_id", [], as_thread=True),
                *self.env["discuss.channel.member"]._to_store_persona("avatar_card"),
                "seen_message_id",
            ],
        ).bus_send()

    def _set_new_message_separator(self, message_id):
        """
        :param message_id: id of the message above which the new message
            separator should be displayed.
        """
        self.ensure_one()
        if message_id == self.new_message_separator:
            return
        self.new_message_separator = message_id

    def _get_html_link_title(self):
        return self.partner_id.name if self.partner_id else self.guest_id.name

    def _get_html_link(self, *args, for_persona=False, **kwargs):
        if not for_persona:
            return self._get_html_link(*args, **kwargs)
        if self.partner_id:
            return self.partner_id._get_html_link(title=f"@{self._get_html_link_title()}")
        return Markup("<strong>%s</strong>") % self.guest_id.name
