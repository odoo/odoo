# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from odoo.osv import expression


class ChannelPartner(models.Model):
    _name = 'mail.channel.partner'
    _description = 'Listeners of a Channel'
    _table = 'mail_channel_partner'

    # identity
    partner_id = fields.Many2one('res.partner', string='Recipient', ondelete='cascade', index=True)
    guest_id = fields.Many2one(string="Guest", comodel_name='mail.guest', ondelete='cascade', readonly=True, index=True)
    partner_email = fields.Char('Email', related='partner_id.email', related_sudo=False)
    # channel
    channel_id = fields.Many2one('mail.channel', string='Channel', ondelete='cascade', readonly=True, required=True)
    # state
    custom_channel_name = fields.Char('Custom channel name')
    fetched_message_id = fields.Many2one('mail.message', string='Last Fetched')
    seen_message_id = fields.Many2one('mail.message', string='Last Seen')
    fold_state = fields.Selection([('open', 'Open'), ('folded', 'Folded'), ('closed', 'Closed')], string='Conversation Fold State', default='open')
    is_minimized = fields.Boolean("Conversation is minimized")
    is_pinned = fields.Boolean("Is pinned on the interface", default=True)
    last_interest_dt = fields.Datetime("Last Interest", default=fields.Datetime.now, help="Contains the date and time of the last interesting event that happened in this channel for this partner. This includes: creating, joining, pinning, and new message posted.")
    # RTC
    rtc_session_ids = fields.One2many(string="RTC Sessions", comodel_name='mail.channel.rtc.session', inverse_name='channel_partner_id')
    rtc_inviting_session_id = fields.Many2one('mail.channel.rtc.session', string='Ringing session')

    def name_get(self):
        return [(record.id, record.partner_id.name or record.guest_id.name) for record in self]

    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        domain = [[('partner_id', operator, name)], [('guest_id', operator, name)]]
        if '!' in operator or 'not' in operator:
            domain = expression.AND(domain)
        else:
            domain = expression.OR(domain)
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def init(self):
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS mail_channel_partner_partner_unique ON %s (channel_id, partner_id) WHERE partner_id IS NOT NULL" % self._table)
        self.env.cr.execute("CREATE UNIQUE INDEX IF NOT EXISTS mail_channel_partner_guest_unique ON %s (channel_id, guest_id) WHERE guest_id IS NOT NULL" % self._table)

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
        return super(ChannelPartner, self).create(vals_list)

    def write(self, vals):
        for channel_partner in self:
            for field_name in {'channel_id', 'partner_id', 'guest_id'}:
                if field_name in vals and vals[field_name] != channel_partner[field_name].id:
                    raise AccessError(_('You can not write on %(field_name)s.', field_name=field_name))
        return super(ChannelPartner, self).write(vals)

    def unlink(self):
        self.sudo().rtc_session_ids.unlink()
        return super().unlink()

    @api.model
    def _get_as_sudo_from_request_or_raise(self, request, channel_id):
        channel_partner = self._get_as_sudo_from_request(request=request, channel_id=channel_id)
        if not channel_partner:
            raise NotFound()
        return channel_partner

    @api.model
    def _get_as_sudo_from_request(self, request, channel_id):
        """ Seeks a channel partner matching the provided `channel_id` and the
        current user or guest.

        :param channel_id: The id of the channel of which the user/guest is
            expected to be member.
        :type channel_id: int
        :return: A record set containing the channel partner if found, or an
            empty record set otherwise. In case of guest, the record is returned
            with the 'guest' record in the context.
        :rtype: mail.channel.partner
        """
        if request.session.uid:
            return self.env['mail.channel.partner'].sudo().search([('channel_id', '=', channel_id), ('partner_id', '=', self.env.user.partner_id.id)], limit=1)
        guest = self.env['mail.guest']._get_guest_from_request(request)
        if guest:
            return guest.env['mail.channel.partner'].sudo().search([('channel_id', '=', channel_id), ('guest_id', '=', guest.id)], limit=1)
        return self.env['mail.channel.partner'].sudo()

    # --------------------------------------------------------------------------
    # RTC (voice/video)
    # --------------------------------------------------------------------------

    def _rtc_join_call(self, check_rtc_session_ids=None):
        self.ensure_one()
        check_rtc_session_ids = (check_rtc_session_ids or []) + self.rtc_session_ids.ids
        self.channel_id._rtc_cancel_invitations(partner_ids=self.partner_id.ids, guest_ids=self.guest_id.ids)
        self.rtc_session_ids.unlink()
        rtc_session = self.env['mail.channel.rtc.session'].create({'channel_partner_id': self.id})
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
            invited_partners, invited_guests = self._rtc_invite_members()
            if invited_guests:
                res['invitedGuests'] = [('insert', [{'id': guest.id, 'name': guest.name} for guest in invited_guests])]
            if invited_partners:
                res['invitedPartners'] = [('insert', [{'id': partner.id, 'name': partner.name} for partner in invited_partners])]
        return res

    def _rtc_leave_call(self):
        self.ensure_one()
        if self.rtc_session_ids:
            self.rtc_session_ids.unlink()
        else:
            return self.channel_id._rtc_cancel_invitations(partner_ids=self.partner_id.ids, guest_ids=self.guest_id.ids)

    def _rtc_sync_sessions(self, check_rtc_session_ids=None):
        """Synchronize the RTC sessions for self channel partner.
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

    def _rtc_invite_members(self, partner_ids=None, guest_ids=None):
        """ Sends invitations to join the RTC call to all connected members of the thread who are not already invited.
            :param list partner_ids: list of the partner ids to invite
            :param list guest_ids: list of the guest ids to invite

            if either partner_ids or guest_ids is set, only the specified ids will be invited.
        """
        self.ensure_one()
        channel_partner_domain = [
            ('channel_id', '=', self.channel_id.id),
            ('rtc_inviting_session_id', '=', False),
            ('rtc_session_ids', '=', False),
        ]
        if partner_ids or guest_ids:
            channel_partner_domain = expression.AND([channel_partner_domain, [
                '|',
                ('partner_id', 'in', partner_ids or []),
                ('guest_id', 'in', guest_ids or []),
            ]])
        invitation_notifications = []
        invited_partners = self.env['res.partner']
        invited_guests = self.env['mail.guest']
        for member in self.env['mail.channel.partner'].search(channel_partner_domain):
            member.rtc_inviting_session_id = self.rtc_session_ids.id
            if member.partner_id:
                invited_partners |= member.partner_id
                target = member.partner_id
            else:
                invited_guests |= member.guest_id
                target = member.guest_id
            invitation_notifications.append((target, 'mail.channel/insert', {
                'id': self.channel_id.id,
                'rtcInvitingSession': [('insert', self.rtc_session_ids._mail_rtc_session_format())],
            }))
        self.env['bus.bus']._sendmany(invitation_notifications)
        if invited_guests or invited_partners:
            channel_data = {'id': self.channel_id.id}
            if invited_guests:
                channel_data['invitedGuests'] = [('insert', [{'id': guest.id, 'name': guest.name} for guest in invited_guests])]
            if invited_partners:
                channel_data['invitedPartners'] = [('insert', [{'id': partner.id, 'name': partner.name} for partner in invited_partners])]
            self.env['bus.bus']._sendone(self.channel_id, 'mail.channel/insert', channel_data)
        return invited_partners, invited_guests
