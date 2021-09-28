# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class MailRtcSession(models.Model):
    _name = 'mail.channel.rtc.session'
    _description = 'Mail RTC session'

    channel_partner_id = fields.Many2one('mail.channel.partner', index=True, required=True, ondelete='cascade')
    channel_id = fields.Many2one('mail.channel', related='channel_partner_id.channel_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', related='channel_partner_id.partner_id', string="Partner")
    guest_id = fields.Many2one('mail.guest', related='channel_partner_id.guest_id')

    write_date = fields.Datetime("Last Updated On", index=True)

    is_screen_sharing_on = fields.Boolean(string="Is sharing the screen")
    is_camera_on = fields.Boolean(string="Is sending user video")
    is_muted = fields.Boolean(string="Is microphone muted")
    is_deaf = fields.Boolean(string="Has disabled incoming sound")

    _sql_constraints = [
        ('channel_partner_unique', 'UNIQUE(channel_partner_id)',
         'There can only be one rtc session per channel partner')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        rtc_sessions = super().create(vals_list)
        self.env['bus.bus'].sendmany([((self._cr.dbname, 'mail.channel', channel.id), {
            'type': 'rtc_sessions_update',
            'payload': {
                'id': channel.id,
                'rtcSessions': [('insert', sessions_data)],
            },
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
        self.env['bus.bus'].sendmany([((self._cr.dbname, 'mail.channel', channel.id), {
            'type': 'rtc_sessions_update',
            'payload': {
                'id': channel.id,
                'rtcSessions': [('insert-and-unlink', [{'id': session_data['id']} for session_data in sessions_data])],
            },
        }) for channel, sessions_data in self._mail_rtc_session_format_by_channel().items()])
        return super().unlink()

    def _update_and_broadcast(self, values):
        """ Updates the session and notifies all members of the channel
            of the change.
        """
        valid_values = {'is_screen_sharing_on', 'is_camera_on', 'is_muted', 'is_deaf'}
        self.write({key: values[key] for key in valid_values if key in valid_values})
        session_data = self._mail_rtc_session_format()
        self.env['bus.bus'].sendone((self._cr.dbname, 'mail.channel', self.channel_id.id), {
            'type': 'mail.rtc_session_update',
            'payload': session_data,
        })

    @api.autovacuum
    def _gc_inactive_sessions(self):
        """ Garbage collect sessions that aren't active anymore,
            this can happen when the server or the user's browser crash
            or when the user's odoo session ends.
        """
        rtc_sessions = self.search([('write_date', '<', fields.Datetime.now() - relativedelta(minutes=1))])
        rtc_sessions._disconnect()

    def action_disconnect(self):
        self._disconnect()

    def _disconnect(self):
        """ Unlinks the sessions and notifies the associated partners/guests that
            their session ended.
        """
        notifications = []
        for rtc_session in self:
            model_name, record_id = ('mail.guest', rtc_session.guest_id.id) if rtc_session.guest_id else ('res.partner', rtc_session.partner_id.id)
            notifications.append([
                (self._cr.dbname, model_name, record_id),
                {
                    'type': 'rtc_session_ended',
                    'payload': {
                        'sessionId': rtc_session.id,
                    },
                },
            ])
        self.unlink()
        self.env['bus.bus'].sendmany(notifications)

    def _notify_peers(self, notifications):
        """ Used for peer-to-peer communication,
            guarantees that the sender is the current guest or partner.

            :param notifications: list of tuple with the following elements:
                - target_session_ids: a list of mail.channel.rtc.session ids
                - content: a string with the content to be sent to the targets
        """
        self.ensure_one()
        payload_by_target = defaultdict(lambda: {'sender': self.id, 'notifications': []})
        for target_session_ids, content in notifications:
            for target_session in self.env['mail.channel.rtc.session'].browse(target_session_ids).exists():
                model, record_id = ('mail.guest', target_session.guest_id.id) if target_session.guest_id else ('res.partner', target_session.partner_id.id)
                payload_by_target[(self._cr.dbname, model, record_id)]['notifications'].append(content)
        return self.env['bus.bus'].sendmany([(target, {
            'type': 'rtc_peer_notification',
            'payload': payload,
        }) for target, payload in payload_by_target.items()])

    def _mail_rtc_session_format(self):
        self.ensure_one()
        vals = {
            'id': self.id,
            'isCameraOn': self.is_camera_on,
            'isDeaf': self.is_deaf,
            'isMuted': self.is_muted,
            'isScreenSharingOn': self.is_screen_sharing_on,
        }
        if self.guest_id:
            vals['guest'] = [('insert', {
                'id': self.guest_id.id,
                'name': self.guest_id.name,
            })]
        else:
            vals['partner'] = [('insert', {
                'id': self.partner_id.id,
                'name': self.partner_id.name,
            })]
        return vals

    def _mail_rtc_session_format_by_channel(self):
        data = {}
        for rtc_session in self:
            data.setdefault(rtc_session.channel_id, []).append(rtc_session._mail_rtc_session_format())
        return data
