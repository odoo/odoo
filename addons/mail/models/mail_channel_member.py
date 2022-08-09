# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from odoo.osv import expression


class ChannelMember(models.Model):
    _name = 'mail.channel.member'
    _description = 'Listeners of a Channel'
    _table = 'mail_channel_member'
    _rec_names_search = ['partner_id', 'guest_id']

    # identity
    partner_id = fields.Many2one('res.partner', string='Recipient', ondelete='cascade', index=True)
    guest_id = fields.Many2one(string="Guest", comodel_name='mail.guest', ondelete='cascade', readonly=True, index=True)
    partner_email = fields.Char('Email', related='partner_id.email', readonly=False)
    # channel
    channel_id = fields.Many2one('mail.channel', string='Channel', ondelete='cascade', readonly=True, required=True)
    # state
    custom_channel_name = fields.Char('Custom channel name')
    fetched_message_id = fields.Many2one('mail.message', string='Last Fetched')
    seen_message_id = fields.Many2one('mail.message', string='Last Seen')
    message_unread_counter = fields.Integer('Unread Messages Counter', compute='_compute_message_unread', compute_sudo=True)
    fold_state = fields.Selection([('open', 'Open'), ('folded', 'Folded'), ('closed', 'Closed')], string='Conversation Fold State', default='open')
    is_minimized = fields.Boolean("Conversation is minimized")
    is_pinned = fields.Boolean("Is pinned on the interface", default=True)
    last_interest_dt = fields.Datetime("Last Interest", default=fields.Datetime.now, help="Contains the date and time of the last interesting event that happened in this channel for this partner. This includes: creating, joining, pinning, and new message posted.")
    last_seen_dt = fields.Datetime("Last seen date")
    # RTC
    rtc_session_ids = fields.One2many(string="RTC Sessions", comodel_name='mail.channel.rtc.session', inverse_name='channel_member_id')
    rtc_inviting_session_id = fields.Many2one('mail.channel.rtc.session', string='Ringing session')

    @api.depends('channel_id.message_ids', 'seen_message_id')
    def _compute_message_unread(self):
        self.env['mail.message'].flush_model()
        self.flush_recordset(['channel_id', 'seen_message_id'])
        self.env.cr.execute("""
                 SELECT count(mail_message.id) AS count,
                        mail_channel_member.id
                   FROM mail_message
             INNER JOIN mail_channel_member
                     ON mail_channel_member.channel_id = mail_message.res_id
                  WHERE mail_message.model = 'mail.channel'
                    AND mail_message.message_type NOT IN ('notification', 'user_notification')
                    AND (
                        mail_message.id > mail_channel_member.seen_message_id
                     OR mail_channel_member.seen_message_id IS NULL
                    )
                    AND mail_channel_member.id IN %(ids)s
               GROUP BY mail_channel_member.id
        """, {'ids': tuple(self.ids)})
        unread_counter_by_member = {res['id']: res['count'] for res in self.env.cr.dictfetchall()}
        for member in self:
            member.message_unread_counter = unread_counter_by_member.get(member.id)

    def name_get(self):
        return [(record.id, record.partner_id.name or record.guest_id.name) for record in self]

    def init(self):
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS mail_channel_member_partner_unique ON %s (channel_id, partner_id) WHERE partner_id IS NOT NULL" % self._table)
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS mail_channel_member_guest_unique ON %s (channel_id, guest_id) WHERE guest_id IS NOT NULL" % self._table)

    _sql_constraints = [
        ("partner_or_guest_exists", "CHECK((partner_id IS NOT NULL AND guest_id IS NULL) OR (partner_id IS NULL AND guest_id IS NOT NULL))", "A channel member must be a partner or a guest."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Similar access rule as the access rule of the mail channel.

        It can not be implemented in XML, because when the record will be created, the
        partner will be added in the channel and the security rule will always authorize
        the creation.
        """
        if not self.env.is_admin():
            for vals in vals_list:
                if 'channel_id' in vals:
                    channel_id = self.env['mail.channel'].browse(vals['channel_id'])
                    if not channel_id._can_invite(vals.get('partner_id')):
                        raise AccessError(_('This user can not be added in this channel'))
        return super().create(vals_list)

    def write(self, vals):
        for channel_member in self:
            for field_name in {'channel_id', 'partner_id', 'guest_id'}:
                if field_name in vals and vals[field_name] != channel_member[field_name].id:
                    raise AccessError(_('You can not write on %(field_name)s.', field_name=field_name))
        return super().write(vals)

    def unlink(self):
        self.sudo().rtc_session_ids.unlink()
        return super().unlink()

    @api.model
    def _get_as_sudo_from_request_or_raise(self, request, channel_id):
        channel_member = self._get_as_sudo_from_request(request=request, channel_id=channel_id)
        if not channel_member:
            raise NotFound()
        return channel_member

    @api.model
    def _get_as_sudo_from_request(self, request, channel_id):
        """ Seeks a channel member matching the provided `channel_id` and the
        current user or guest.

        :param channel_id: The id of the channel of which the user/guest is
            expected to be member.
        :type channel_id: int
        :return: A record set containing the channel member if found, or an
            empty record set otherwise. In case of guest, the record is returned
            with the 'guest' record in the context.
        :rtype: mail.channel.member
        """
        if request.session.uid:
            return self.env['mail.channel.member'].sudo().search([('channel_id', '=', channel_id), ('partner_id', '=', self.env.user.partner_id.id)], limit=1)
        guest = self.env['mail.guest']._get_guest_from_request(request)
        if guest:
            return guest.env['mail.channel.member'].sudo().search([('channel_id', '=', channel_id), ('guest_id', '=', guest.id)], limit=1)
        return self.env['mail.channel.member'].sudo()

    def mail_channel_member_format(self):
        members_formatted_data = []
        for member in self:
            if member.partner_id:
                persona = {
                    'partner': {
                        'id': member.partner_id.id,
                        'name': member.partner_id.name,
                        'im_status': member.partner_id.im_status,
                    },
                }
            if member.guest_id:
                persona = {
                    'guest': {
                        'id': member.guest_id.id,
                        'name': member.guest_id.name,
                        'im_status': member.guest_id.im_status,
                    },
                }
            members_formatted_data.append({
                'id': member.id,
                'channel': {'id': member.channel_id.id},
                'persona': persona,
            })
        return members_formatted_data

    # --------------------------------------------------------------------------
    # RTC (voice/video)
    # --------------------------------------------------------------------------

    def _rtc_join_call(self, check_rtc_session_ids=None):
        self.ensure_one()
        check_rtc_session_ids = (check_rtc_session_ids or []) + self.rtc_session_ids.ids
        self.channel_id._rtc_cancel_invitations(member_ids=self.ids)
        self.rtc_session_ids.unlink()
        rtc_session = self.env['mail.channel.rtc.session'].create({'channel_member_id': self.id})
        current_rtc_sessions, outdated_rtc_sessions = self._rtc_sync_sessions(check_rtc_session_ids=check_rtc_session_ids)
        res = {
            'iceServers': self.env['mail.ice.server']._get_ice_servers() or False,
            'rtcSessions': [
                ('insert', [rtc_session_sudo._mail_rtc_session_format() for rtc_session_sudo in current_rtc_sessions]),
                ('insert-and-unlink', [{'id': missing_rtc_session_sudo.id} for missing_rtc_session_sudo in outdated_rtc_sessions]),
            ],
            'sessionId': rtc_session.id,
        }
        if len(self.channel_id.rtc_session_ids) == 1 and self.channel_id.channel_type in {'chat', 'group'}:
            self.channel_id.message_post(body=_("%s started a live conference", self.partner_id.name or self.guest_id.name), message_type='notification')
            invited_members = self._rtc_invite_members()
            if invited_members:
                res['invitedMembers'] = [('insert', invited_members.mail_channel_member_format())]
        return res

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
        check_rtc_sessions = self.env['mail.channel.rtc.session'].browse([int(check_rtc_session_id) for check_rtc_session_id in (check_rtc_session_ids or [])])
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
        members = self.env['mail.channel.member'].search(channel_member_domain)
        for member in members:
            member.rtc_inviting_session_id = self.rtc_session_ids.id
            if member.partner_id:
                target = member.partner_id
            else:
                target = member.guest_id
            invitation_notifications.append((target, 'mail.thread/insert', {
                'id': self.channel_id.id,
                'model': 'mail.channel',
                'rtcInvitingSession': [('insert', self.rtc_session_ids._mail_rtc_session_format())],
            }))
        self.env['bus.bus']._sendmany(invitation_notifications)
        if members:
            channel_data = {'id': self.channel_id.id, 'model': 'mail.channel'}
            channel_data['invitedMembers'] = [('insert', members.mail_channel_member_format())]
            self.env['bus.bus']._sendone(self.channel_id, 'mail.thread/insert', channel_data)
        return members
