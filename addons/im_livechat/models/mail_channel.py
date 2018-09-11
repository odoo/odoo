# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ChannelPartner(models.Model):
    _inherit = 'mail.channel.partner'

    @api.model
    def unpin_old_livechat_sessions(self):
        """ Unpin livechat sessions with no activity for at least one day to
            clean the operator's interface """
        self.env.cr.execute("""
            UPDATE mail_channel_partner
            SET is_pinned = false
            WHERE id in (
                SELECT cp.id FROM mail_channel_partner cp
                INNER JOIN mail_channel c on c.id = cp.channel_id
                WHERE c.channel_type = 'livechat' AND cp.is_pinned is true AND
                    cp.write_date < current_timestamp - interval '1 day'
            )
        """)


class MailChannel(models.Model):
    """ Chat Session
        Reprensenting a conversation between users.
        It extends the base method for anonymous usage.
    """

    _name = 'mail.channel'
    _inherit = ['mail.channel', 'rating.mixin']

    anonymous_name = fields.Char('Anonymous Name')
    create_date = fields.Datetime('Create Date', required=True)
    channel_type = fields.Selection(selection_add=[('livechat', 'Livechat Conversation')])
    livechat_channel_id = fields.Many2one('im_livechat.channel', 'Channel')

    @api.multi
    def _channel_message_notifications(self, message):
        """ When a anonymous user create a mail.channel, the operator is not notify (to avoid massive polling when
            clicking on livechat button). So when the anonymous person is sending its FIRST message, the channel header
            should be added to the notification, since the user cannot be listining to the channel.
        """
        notifications = super(MailChannel, self)._channel_message_notifications(message)
        message_values_dict = notifications[0][1] if len(notifications) else dict(message.message_format()[0])
        for channel in self:
            # add uuid for private livechat channels to allow anonymous to listen
            if channel.channel_type == 'livechat':
                notifications.append([channel.uuid, message_values_dict])
        if not message.author_id:
            unpinned_channel_partner = self.mapped('channel_last_seen_partner_ids').filtered(lambda cp: not cp.is_pinned)
            if unpinned_channel_partner:
                unpinned_channel_partner.write({'is_pinned': True})
                notifications = self._channel_channel_notifications(unpinned_channel_partner.mapped('partner_id').ids) + notifications
        return notifications

    @api.multi
    def channel_info(self, extra_info=False):
        """ Extends the channel header by adding the livechat operator and the 'anonymous' profile
            :rtype : list(dict)
        """
        channel_infos = super(MailChannel, self).channel_info(extra_info)
        # add the operator id
        if self.env.context.get('im_livechat_operator_partner_id'):
            partner_name = self.env['res.partner'].browse(self.env.context.get('im_livechat_operator_partner_id')).name_get()[0]
            for channel_info in channel_infos:
                channel_info['operator_pid'] = partner_name
        channel_infos_dict = dict((c['id'], c) for c in channel_infos)
        for channel in self:
            # add the anonymous name
            if channel.anonymous_name:
                channel_infos_dict[channel.id]['anonymous_name'] = channel.anonymous_name
            # add the last message date
            if channel.channel_type == 'livechat':
                last_msg = self.env['mail.message'].search([("channel_ids", "in", [channel.id])], limit=1)
                if last_msg:
                    channel_infos_dict[channel.id]['last_message_date'] = last_msg.date
        return list(channel_infos_dict.values())

    @api.model
    def channel_fetch_slot(self):
        values = super(MailChannel, self).channel_fetch_slot()
        pinned_channels = self.env['mail.channel.partner'].search([('partner_id', '=', self.env.user.partner_id.id), ('is_pinned', '=', True)]).mapped('channel_id')
        values['channel_livechat'] = self.search([('channel_type', '=', 'livechat'), ('id', 'in', pinned_channels.ids)]).channel_info()
        return values

    @api.model
    def remove_empty_livechat_sessions(self):
        hours = 1  # never remove empty session created within the last hour
        self.env.cr.execute("""
            SELECT id as id
            FROM mail_channel C
            WHERE NOT EXISTS (
                SELECT *
                FROM mail_message_mail_channel_rel R
                WHERE R.mail_channel_id = C.id
            ) AND C.channel_type = 'livechat' AND livechat_channel_id IS NOT NULL AND
                COALESCE(write_date, create_date, (now() at time zone 'UTC'))::timestamp
                < ((now() at time zone 'UTC') - interval %s)""", ("%s hours" % hours,))
        empty_channel_ids = [item['id'] for item in self.env.cr.dictfetchall()]
        self.browse(empty_channel_ids).unlink()

    @api.model
    def get_empty_list_help(self, help):
        if help:
            return '<p>%s</p>' % (help)
        return super(MailChannel, self).get_empty_list_help(help)

    def _define_command_history(self):
        return {
            'channel_types': ['livechat'],
            'help': _('See 15 last visited pages')
        }

    def _execute_command_history(self, **kwargs):
        notification = []
        notification_values = {
            '_type': 'history_command',
        }
        notification.append([self.uuid, dict(notification_values)])
        return self.env['bus.bus'].sendmany(notification)

    def _send_history_message(self, pid, page_history):
        message_body = _('No history found')
        if page_history:
            html_links = ['<li><a href="%s" target="_blank">%s</a></li>' % (page, page) for page in page_history]
            message_body = '<span class="o_mail_notification"><ul>%s</ul></span>' % (''.join(html_links))
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner', pid), {
            'body': message_body,
            'channel_ids': self.ids,
            'info': 'transient_message',
        })

    # Rating Mixin

    def rating_get_parent_model_name(self, values):
        return 'im_livechat.channel'

    def rating_get_parent_id(self):
        return self.livechat_channel_id.id
