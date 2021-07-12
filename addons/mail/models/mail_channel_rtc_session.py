# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def _update_and_broadcast(self, values):
        """ Updates the session and notifies all members of the channel
            of the change.
        """
        valid_values = {'is_screen_sharing_on', 'is_camera_on', 'is_muted', 'is_deaf'}
        self.write({key: values[key] for key in valid_values if key in valid_values})
        session_data = self._mail_rtc_session_format()
        self.env['bus.bus'].sendone((self._cr.dbname, 'mail.channel', self.channel_id.id), {
            'type': 'rtc_session_data_update',
            'payload': {
                'rtcSession': session_data,
            },
        })

    @api.autovacuum
    def _gc_inactive_sessions(self):
        """ Garbage collect sessions that aren't active anymore,
            this can happen when the server or the user's browser crash
            or when the user's odoo session ends.
        """
        sessions = self.search([
            ('write_date', '<', fields.Datetime.now() - relativedelta(days=1))
        ])
        if not sessions:
            return
        channel_ids = sessions.channel_id
        sessions.unlink()
        channel_ids._notify_rtc_sessions_change()

    def action_disconnect(self):
        channels = self.channel_id
        self._disconnect()
        if channels:
            channels._notify_rtc_sessions_change()

    def _disconnect(self):
        """ Unlinks the sessions and notifies the associated partners/guests that
            their session ended.
        """
        notifications = []
        for record in self:
            model, record_id = ('mail.guest', record.guest_id.id) if record.guest_id else ('res.partner', record.partner_id.id)
            notifications.append([
                (self._cr.dbname, model, record_id),
                {
                    'type': 'rtc_session_ended',
                    'payload': {
                        'sessionId': record.id,
                    },
                },
            ])
        self.unlink()
        self.env['bus.bus'].sendmany(notifications)

    def _notify_peers(self, target_session_ids, content):
        """ Used for peer-to-peer communication,
            guarantees that the sender is the current guest or partner.

            :param target_session_ids: a list of mail.channel.rtc.session ids
            :param content: a dict with the content to be sent to the targets
        """
        notifications = []
        target_sessions = self.search([('id', 'in', [int(target) for target in target_session_ids]), ('channel_id', '=', self.channel_id.id)])
        for session in target_sessions:
            model, record_id = ('mail.guest', session.guest_id.id) if session.guest_id else ('res.partner', session.partner_id.id)
            notifications.append([
                (self._cr.dbname, model, record_id),
                {
                    'type': 'rtc_peer_notification',
                    'payload': {
                        'sender': self.id,
                        'content': content,
                    },
                },
            ])
        return self.env['bus.bus'].sendmany(notifications)

    def _mail_rtc_session_format(self):
        vals = {
            'id': self.id,
            'is_screen_sharing_on': self.is_screen_sharing_on,
            'is_muted': self.is_muted,
            'is_deaf': self.is_deaf,
            'is_camera_on': self.is_camera_on,
        }
        if self.guest_id:
            vals['guest'] = {
                'id': self.guest_id.id,
                'name': self.guest_id.name,
            }
        else:
            vals['partner'] = {
                'id': self.partner_id.id,
                'name': self.partner_id.name,
            }
        return vals

    def _mail_rtc_session_format_by_channel(self):
        data = {}
        for record in self:
            data.setdefault(record.channel_id.id, []).append(record._mail_rtc_session_format())
        return data
