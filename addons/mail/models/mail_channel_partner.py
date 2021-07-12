# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class ChannelPartner(models.Model):
    _name = 'mail.channel.partner'
    _description = 'Listeners of a Channel'
    _table = 'mail_channel_partner'
    _rec_name = 'partner_id'

    # identity
    partner_id = fields.Many2one('res.partner', string='Recipient', ondelete='cascade', readonly=True, index=True)
    guest_id = fields.Many2one(string="Guest", comodel_name='mail.guest', ondelete='cascade', readonly=True, index=True)
    partner_email = fields.Char('Email', related='partner_id.email', readonly=False)
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
    rtc_inviting_session_id = fields.Many2one('mail.channel.rtc.session', string='Ringing session')

    def _remove_rtc_invitation(self):
        """ Removes the invitation to the rtc call and notifies the inviting partner if removed. """
        notifications = []
        for record in self:
            if not record.rtc_inviting_session_id:
                continue
            model, record_id = ('mail.guest', record.rtc_inviting_session_id.guest_id.id) if record.rtc_inviting_session_id.guest_id else (
                'res.partner', record.rtc_inviting_session_id.partner_id.id)
            payload = {'channelId': record.channel_id.id}
            if record.partner_id:
                payload['partnerId'] = record.partner_id.id
            else:
                payload['guestId'] = record.guest_id.id
            notifications.append([
                (self._cr.dbname, model, record_id),
                {
                    'type': 'rtc_outgoing_invitation_ended',
                    'payload': payload,
                },
            ])
        self.write({'rtc_inviting_session_id': False})
        self.env['bus.bus'].sendmany(notifications)

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
        return self.env['mail.channel.partner']
