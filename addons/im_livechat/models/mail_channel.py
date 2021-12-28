# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import html_escape


class MailChannel(models.Model):
    """ Chat Session
        Reprensenting a conversation between users.
        It extends the base method for anonymous usage.
    """

    _name = 'mail.channel'
    _inherit = ['mail.channel', 'rating.mixin']

    anonymous_name = fields.Char('Anonymous Name')
    channel_type = fields.Selection(selection_add=[('livechat', 'Livechat Conversation')])
    livechat_active = fields.Boolean('Is livechat ongoing?', help='Livechat session is active until visitor leave the conversation.')
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

    def _channel_message_notifications(self, message, message_format=False):
        """ When a anonymous user create a mail.channel, the operator is not notify (to avoid massive polling when
            clicking on livechat button). So when the anonymous person is sending its FIRST message, the channel header
            should be added to the notification, since the user cannot be listining to the channel.
        """
        notifications = super()._channel_message_notifications(message=message, message_format=message_format)
        for channel in self:
            # add uuid for private livechat channels to allow anonymous to listen
            if channel.channel_type == 'livechat' and channel.public == 'private':
                notifications.append([channel.uuid, 'mail.channel/new_message', notifications[0][2]])
        if not message.author_id:
            unpinned_channel_partner = self.channel_last_seen_partner_ids.filtered(lambda cp: not cp.is_pinned)
            if unpinned_channel_partner:
                unpinned_channel_partner.write({'is_pinned': True})
                notifications = self._channel_channel_notifications(unpinned_channel_partner.mapped('partner_id').ids) + notifications
        return notifications

    def channel_info(self):
        """ Extends the channel header by adding the livechat operator and the 'anonymous' profile
            :rtype : list(dict)
        """
        channel_infos = super().channel_info()
        channel_infos_dict = dict((c['id'], c) for c in channel_infos)
        for channel in self:
            # add the last message date
            if channel.channel_type == 'livechat':
                # add the operator id
                if channel.livechat_operator_id:
                    display_name = channel.livechat_operator_id.user_livechat_username or channel.livechat_operator_id.display_name
                    channel_infos_dict[channel.id]['operator_pid'] = (channel.livechat_operator_id.id, display_name.replace(',', ''))
                # add the anonymous or partner name
                channel_infos_dict[channel.id]['livechat_visitor'] = channel._channel_get_livechat_visitor_info()
        return list(channel_infos_dict.values())

    def _channel_info_format_member(self, partner, partner_info):
        """Override to remove sensitive information in livechat."""
        if self.channel_type == 'livechat':
            return {
                'active': partner.active,
                'id': partner.id,
                'name': partner.user_livechat_username or partner.name,  # for API compatibility in stable
                'email': False,  # for API compatibility in stable
                'im_status': False,  # for API compatibility in stable
                'livechat_username': partner.user_livechat_username,
            }
        return super()._channel_info_format_member(partner=partner, partner_info=partner_info)

    def _notify_typing_partner_data(self):
        """Override to remove name and return livechat username if applicable."""
        data = super()._notify_typing_partner_data()
        if self.channel_type == 'livechat' and self.env.user.partner_id.user_livechat_username:
            data['partner_name'] = self.env.user.partner_id.user_livechat_username  # for API compatibility in stable
            data['livechat_username'] = self.env.user.partner_id.user_livechat_username
        return data

    def _channel_get_livechat_visitor_info(self):
        self.ensure_one()
        # remove active test to ensure public partner is taken into account
        channel_partner_ids = self.with_context(active_test=False).channel_partner_ids
        partners = channel_partner_ids - self.livechat_operator_id
        if not partners:
            # operator probably testing the livechat with his own user
            partners = channel_partner_ids
        first_partner = partners and partners[0]
        if first_partner and (not first_partner.user_ids or not any(user._is_public() for user in first_partner.user_ids)):
            # legit non-public partner
            return {
                'country': first_partner.country_id.name_get()[0] if first_partner.country_id else False,
                'id': first_partner.id,
                'name': first_partner.name,
            }
        return {
            'country': self.country_id.name_get()[0] if self.country_id else False,
            'id': False,
            'name': self.anonymous_name or _("Visitor"),
        }

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

    @api.autovacuum
    def _gc_empty_livechat_sessions(self):
        hours = 1  # never remove empty session created within the last hour
        self.env.cr.execute("""
            SELECT id as id
            FROM mail_channel C
            WHERE NOT EXISTS (
                SELECT *
                FROM mail_message M
                WHERE M.res_id = C.id AND m.model = 'mail.channel'
            ) AND C.channel_type = 'livechat' AND livechat_channel_id IS NOT NULL AND
                COALESCE(write_date, create_date, (now() at time zone 'UTC'))::timestamp
                < ((now() at time zone 'UTC') - interval %s)""", ("%s hours" % hours,))
        empty_channel_ids = [item['id'] for item in self.env.cr.dictfetchall()]
        self.browse(empty_channel_ids).unlink()

    def _execute_command_help_message_extra(self):
        msg = super(MailChannel, self)._execute_command_help_message_extra()
        return msg + _("Type <b>:shortcut</b> to insert a canned response in your message.<br>")

    def execute_command_history(self, **kwargs):
        self.env['bus.bus']._sendone(self.uuid, 'im_livechat.history_command', {'id': self.id})

    def _send_history_message(self, pid, page_history):
        message_body = _('No history found')
        if page_history:
            html_links = ['<li><a href="%s" target="_blank">%s</a></li>' % (html_escape(page), html_escape(page)) for page in page_history]
            message_body = '<ul>%s</ul>' % (''.join(html_links))
        self._send_transient_message(self.env['res.partner'].browse(pid), message_body)

    def _get_visitor_leave_message(self, operator=False, cancel=False):
        return _('Visitor has left the conversation.')

    def _close_livechat_session(self, **kwargs):
        """ Set deactivate the livechat channel and notify (the operator) the reason of closing the session."""
        self.ensure_one()
        if self.livechat_active:
            self.livechat_active = False
            # avoid useless notification if the channel is empty
            if not self.message_ids:
                return
            # Notify that the visitor has left the conversation
            self.message_post(author_id=self.env.ref('base.partner_root').id,
                              body=self._get_visitor_leave_message(**kwargs), message_type='comment', subtype_xmlid='mail.mt_comment')

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
        mail_body = template._render(render_context, engine='ir.qweb', minimal_qcontext=True)
        mail_body = self.env['mail.render.mixin']._replace_local_links(mail_body)
        mail = self.env['mail.mail'].sudo().create({
            'subject': _('Conversation with %s', self.livechat_operator_id.user_livechat_username or self.livechat_operator_id.name),
            'email_from': company.catchall_formatted or company.email_formatted,
            'author_id': self.env.user.partner_id.id,
            'email_to': email,
            'body_html': mail_body,
        })
        mail.send()
