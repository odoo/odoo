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
    channel_type = fields.Selection(selection_add=[('livechat', 'Livechat Conversation')])
    livechat_channel_id = fields.Many2one('im_livechat.channel', 'Channel')
    livechat_operator_id = fields.Many2one('res.partner', string='Operator', help="""Operator for this specific channel""")
    country_id = fields.Many2one('res.country', string="Country", help="Country of the visitor of the channel")

    _sql_constraints = [('livechat_operator_id', "CHECK((channel_type = 'livechat' and livechat_operator_id is not null) or (channel_type != 'livechat'))",
                         'Livechat Operator ID is required for a channel of type livechat.')]

    def _compute_is_chat(self):
        super(MailChannel, self)._compute_is_chat()
        for record in self:
            if record.channel_type == 'livechat':
                record.is_chat = True
            else:
                record.is_chat = False

    def _channel_message_notifications(self, message, message_format=False):
        """ When a anonymous user create a mail.channel, the operator is not notify (to avoid massive polling when
            clicking on livechat button). So when the anonymous person is sending its FIRST message, the channel header
            should be added to the notification, since the user cannot be listining to the channel.
        """
        livechat_channels = self.filtered(lambda x: x.channel_type == 'livechat')
        other_channels = self.filtered(lambda x: x.channel_type != 'livechat')
        notifications = super(MailChannel, livechat_channels)._channel_message_notifications(message.with_context(im_livechat_use_username=True)) + \
                        super(MailChannel, other_channels)._channel_message_notifications(message, message_format)
        for channel in self:
            # add uuid for private livechat channels to allow anonymous to listen
            if channel.channel_type == 'livechat' and channel.public == 'private':
                notifications.append([channel.uuid, notifications[0][1]])
        if not message.author_id:
            unpinned_channel_partner = self.mapped('channel_last_seen_partner_ids').filtered(lambda cp: not cp.is_pinned)
            if unpinned_channel_partner:
                unpinned_channel_partner.write({'is_pinned': True})
                notifications = self._channel_channel_notifications(unpinned_channel_partner.mapped('partner_id').ids) + notifications
        return notifications

    def channel_fetch_message(self, last_id=False, limit=20):
        """ Override to add the context of the livechat username."""
        channel = self.with_context(im_livechat_use_username=True) if self.channel_type == 'livechat' else self
        return super(MailChannel, channel).channel_fetch_message(last_id=last_id, limit=limit)

    def channel_info(self, extra_info=False):
        """ Extends the channel header by adding the livechat operator and the 'anonymous' profile
            :rtype : list(dict)
        """
        channel_infos = super(MailChannel, self).channel_info(extra_info)
        channel_infos_dict = dict((c['id'], c) for c in channel_infos)
        for channel in self:
            # add the last message date
            if channel.channel_type == 'livechat':
                # add the operator id
                if channel.livechat_operator_id:
                    channel_infos_dict[channel.id]['operator_pid'] = channel.livechat_operator_id.with_context(im_livechat_use_username=True).name_get()[0]
                # add the anonymous or partner name
                channel_infos_dict[channel.id]['correspondent_name'] = channel._channel_get_livechat_partner_name()
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

    def _channel_get_livechat_partner_name(self):
        if self.livechat_operator_id in self.channel_partner_ids:
            partners = self.channel_partner_ids - self.livechat_operator_id
            if partners:
                partner_name = False
                for partner in partners:
                    if not partner_name:
                        partner_name = partner.name
                    else:
                        partner_name += ', %s' % partner.name
                    if partner.country_id:
                        partner_name += ' (%s)' % partner.country_id.name
                return partner_name
        if self.anonymous_name:
            return self.anonymous_name
        return _("Visitor")

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

    def _rating_get_parent_field_name(self):
        return 'livechat_channel_id'

    def _email_livechat_transcript(self, email):
        company = self.env.user.company_id
        render_context = {
            "company": company,
            "channel": self,
        }
        template = self.env.ref('im_livechat.livechat_email_template')
        mail_body = template.render(render_context, engine='ir.qweb', minimal_qcontext=True)
        mail_body = self.env['mail.thread']._replace_local_links(mail_body)
        mail = self.env['mail.mail'].create({
            'subject': _('Conversation with %s') % self.livechat_operator_id.name,
            'email_from': self.env.company.email,
            'email_to': email,
            'body_html': mail_body,
        })
        mail.send()
