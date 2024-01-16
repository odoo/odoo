# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from ...tools import jwt, discuss

_logger = logging.getLogger(__name__)
SFU_MODE_THRESHOLD = 3


class ChannelMember(models.Model):
    _name = "discuss.channel.member"
    _description = "Channel Member"
    _rec_names_search = ["channel_id", "partner_id", "guest_id"]
    _bypass_create_check = {}

    # identity
    partner_id = fields.Many2one("res.partner", "Partner", ondelete="cascade", index=True)
    guest_id = fields.Many2one("mail.guest", "Guest", ondelete="cascade", index=True)
    is_self = fields.Boolean(compute="_compute_is_self", search="_search_is_self")
    # channel
    channel_id = fields.Many2one("discuss.channel", "Channel", ondelete="cascade", required=True)
    # state
    custom_channel_name = fields.Char('Custom channel name')
    fetched_message_id = fields.Many2one('mail.message', string='Last Fetched', index="btree_not_null")
    seen_message_id = fields.Many2one('mail.message', string='Last Seen', index="btree_not_null")
    message_unread_counter = fields.Integer('Unread Messages Counter', compute='_compute_message_unread', compute_sudo=True)
    fold_state = fields.Selection([('open', 'Open'), ('folded', 'Folded'), ('closed', 'Closed')], string='Conversation Fold State', default='open')
    is_minimized = fields.Boolean("Conversation is minimized")
    custom_notifications = fields.Selection(
        [("mentions", "Mentions Only"), ("no_notif", "Nothing")],
        "Customized Notifications",
        help="All Messages if not specified",
    )
    mute_until_dt = fields.Datetime("Mute notifications until", help="If set, the member will not receive notifications from the channel until this date.")
    is_pinned = fields.Boolean("Is pinned on the interface", default=True)
    last_interest_dt = fields.Datetime("Last Interest", default=fields.Datetime.now, help="Contains the date and time of the last interesting event that happened in this channel for this partner. This includes: creating, joining, pinning, and new message posted.")
    last_seen_dt = fields.Datetime("Last seen date")
    # RTC
    rtc_session_ids = fields.One2many(string="RTC Sessions", comodel_name='discuss.channel.rtc.session', inverse_name='channel_member_id')
    rtc_inviting_session_id = fields.Many2one('discuss.channel.rtc.session', string='Ringing session')

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

    @api.depends("channel_id.message_ids", "seen_message_id")
    def _compute_message_unread(self):
        if self.ids:
            self.env['mail.message'].flush_model()
            self.flush_recordset(['channel_id', 'seen_message_id'])
            self.env.cr.execute("""
                     SELECT count(mail_message.id) AS count,
                            discuss_channel_member.id
                       FROM mail_message
                 INNER JOIN discuss_channel_member
                         ON discuss_channel_member.channel_id = mail_message.res_id
                      WHERE mail_message.model = 'discuss.channel'
                        AND mail_message.message_type NOT IN ('notification', 'user_notification')
                        AND (
                            mail_message.id > discuss_channel_member.seen_message_id
                         OR discuss_channel_member.seen_message_id IS NULL
                        )
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
        return super().create(vals_list)

    def write(self, vals):
        for channel_member in self:
            for field_name in ['channel_id', 'partner_id', 'guest_id']:
                if field_name in vals and vals[field_name] != channel_member[field_name].id:
                    raise AccessError(_('You can not write on %(field_name)s.', field_name=field_name))
        return super().write(vals)

    def unlink(self):
        # sudo: discuss.channel.rtc.session - cascade unlink of sessions for self member
        self.sudo().rtc_session_ids.unlink()  # ensure unlink overrides are applied
        return super().unlink()

    def _notify_typing(self, is_typing):
        """ Broadcast the typing notification to channel members
            :param is_typing: (boolean) tells whether the members are typing or not
        """
        notifications = []
        for member in self:
            formatted_member = member._discuss_channel_member_format().get(member)
            formatted_member['isTyping'] = is_typing
            notifications.append([member.channel_id, 'discuss.channel.member/typing_status', formatted_member])
            notifications.append([member.channel_id.uuid, 'discuss.channel.member/typing_status', formatted_member])  # notify livechat users
        self.env['bus.bus']._sendmany(notifications)

    @api.model
    def _unmute(self):
        # Unmute notifications for the all the channel members whose mute date is passed.
        members = self.search([("mute_until_dt", "<=", fields.Datetime.now())])
        members.write({"mute_until_dt": False})
        notifications = []
        for member in members:
            channel_data = {
                "id": member.channel_id.id,
                "model": "discuss.channel",
                "mute_until_dt": False,
            }
            notifications.append((member.partner_id, "mail.record/insert", {"Thread": channel_data}))
        self.env["bus.bus"]._sendmany(notifications)

    def _discuss_channel_member_format(self, fields=None):
        if not fields:
            fields = {'id': True, 'channel': {}, 'persona': {}}
        members_formatted_data = {}
        for member in self:
            data = {}
            if 'id' in fields:
                data['id'] = member.id
            if 'channel' in fields:
                data['thread'] = member.channel_id._channel_format(fields=fields.get('channel')).get(member.channel_id)
            if 'persona' in fields:
                if member.partner_id:
                    # sudo: res.partner - reading _get_partner_data related to a member is considered acceptable
                    persona = member.sudo()._get_partner_data(fields=fields.get('persona', {}).get('partner'))
                    persona['type'] = "partner"
                if member.guest_id:
                    # sudo: mail.guest - reading _guest_format related to a member is considered acceptable
                    persona = member.guest_id.sudo()._guest_format(fields=fields.get('persona', {}).get('guest')).get(member.guest_id)
                data['persona'] = persona
            if 'custom_notifications' in fields:
                data['custom_notifications'] = member.custom_notifications
            if 'mute_until_dt' in fields:
                data['mute_until_dt'] = member.mute_until_dt
            members_formatted_data[member] = data
        return members_formatted_data

    def _get_partner_data(self, fields=None):
        self.ensure_one()
        return self.partner_id.mail_partner_format(fields=fields).get(self.partner_id)

    # --------------------------------------------------------------------------
    # RTC (voice/video)
    # --------------------------------------------------------------------------

    def _rtc_join_call(self, check_rtc_session_ids=None):
        self.ensure_one()
        check_rtc_session_ids = (check_rtc_session_ids or []) + self.rtc_session_ids.ids
        self.channel_id._rtc_cancel_invitations(member_ids=self.ids)
        self.rtc_session_ids.unlink()
        rtc_session = self.env['discuss.channel.rtc.session'].create({'channel_member_id': self.id})
        current_rtc_sessions, outdated_rtc_sessions = self._rtc_sync_sessions(check_rtc_session_ids=check_rtc_session_ids)
        ice_servers = self.env["mail.ice.server"]._get_ice_servers()
        self._join_sfu(ice_servers)
        res = {
            'iceServers': ice_servers or False,
            'rtcSessions': [
                ('ADD', [rtc_session_sudo._mail_rtc_session_format() for rtc_session_sudo in current_rtc_sessions]),
                ('DELETE', [{'id': missing_rtc_session_sudo.id} for missing_rtc_session_sudo in outdated_rtc_sessions]),
            ],
            'sessionId': rtc_session.id,
            'serverInfo': self._get_rtc_server_info(rtc_session, ice_servers),
        }
        if len(self.channel_id.rtc_session_ids) == 1 and self.channel_id.channel_type in {'chat', 'group'}:
            self.channel_id.message_post(body=_("%s started a live conference", self.partner_id.name or self.guest_id.name), message_type='notification')
            invited_members = self._rtc_invite_members()
            if invited_members:
                res['invitedMembers'] = [('ADD', list(invited_members._discuss_channel_member_format(fields={'id': True, 'channel': {}, 'persona': {'partner': {'id', 'name', 'im_status'}, 'guest': {'id', 'name', 'im_status'}}}).values()))]
        return res

    def _join_sfu(self, ice_servers=None):
        if len(self.channel_id.rtc_session_ids) < SFU_MODE_THRESHOLD:
            if self.channel_id.sfu_channel_uuid:
                self.channel_id.sfu_channel_uuid = None
                self.channel_id.sfu_server_url = None
            return
        elif self.channel_id.sfu_channel_uuid and self.channel_id.sfu_server_url:
            return
        sfu_server_url = discuss.get_sfu_url(self.env)
        if not sfu_server_url:
            return
        sfu_server_key = discuss.get_sfu_key(self.env)
        json_web_token = jwt.sign(
            {"iss": f"{self.get_base_url()}:channel:{self.channel_id.id}"},
            key=sfu_server_key,
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
        notifications = [
            [
                session.guest_id or session.partner_id,
                "discuss.channel.rtc.session/sfu_hot_swap",
                {"serverInfo": self._get_rtc_server_info(session, ice_servers, key=sfu_server_key)},
            ]
            for session in self.channel_id.rtc_session_ids
        ]
        self.env["bus.bus"]._sendmany(notifications)

    def _get_rtc_server_info(self, rtc_session, ice_servers=None, key=None):
        sfu_channel_uuid = self.channel_id.sfu_channel_uuid
        sfu_server_url = self.channel_id.sfu_server_url
        if not sfu_channel_uuid or not sfu_server_url:
            return None
        if not key:
            key = discuss.get_sfu_key(self.env)
        claims = {
            "sfu_channel_uuid": sfu_channel_uuid,
            "session_id": rtc_session.id,
            "ice_servers": ice_servers,
        }
        json_web_token = jwt.sign(claims, key=key, ttl=60 * 60 * 8, algorithm=jwt.Algorithm.HS256)  # 8 hours
        return {"url": sfu_server_url, "jsonWebToken": json_web_token}

    def _rtc_leave_call(self):
        self.ensure_one()
        if self.rtc_session_ids:
            self.rtc_session_ids.unlink()
        else:
            return self.channel_id._rtc_cancel_invitations(member_ids=self.ids)

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

    def _rtc_invite_members(self, member_ids=None):
        """ Sends invitations to join the RTC call to all connected members of the thread who are not already invited,
            if member_ids is set, only the specified ids will be invited.

            :param list member_ids: list of the partner ids to invite
        """
        self.ensure_one()
        channel_member_domain = [
            ('channel_id', '=', self.channel_id.id),
            ('rtc_inviting_session_id', '=', False),
            ('rtc_session_ids', '=', False),
        ]
        if member_ids:
            channel_member_domain = expression.AND([channel_member_domain, [('id', 'in', member_ids)]])
        invitation_notifications = []
        members = self.env['discuss.channel.member'].search(channel_member_domain)
        for member in members:
            member.rtc_inviting_session_id = self.rtc_session_ids.id
            if member.partner_id:
                target = member.partner_id
            else:
                target = member.guest_id
            invitation_notifications.append((target, 'mail.record/insert', {
                'Thread': {
                    'id': self.channel_id.id,
                    'model': 'discuss.channel',
                    'rtcInvitingSession': self.rtc_session_ids._mail_rtc_session_format(),
                }
            }))
        self.env['bus.bus']._sendmany(invitation_notifications)
        if members:
            channel_data = {'id': self.channel_id.id, 'model': 'discuss.channel'}
            channel_data['invitedMembers'] = [('ADD', list(members._discuss_channel_member_format(fields={'id': True, 'channel': {}, 'persona': {'partner': {'id', 'name', 'im_status'}, 'guest': {'id', 'name', 'im_status'}}}).values()))]
            self.env['bus.bus']._sendone(self.channel_id, 'mail.record/insert', {'Thread': channel_data})
        return members
