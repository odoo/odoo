# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import email_normalize, html_escape, html2plaintext, plaintext2html

from markupsafe import Markup


class MailChannel(models.Model):
    """ Chat Session
        Reprensenting a conversation between users.
        It extends the base method for anonymous usage.
    """

    _name = 'mail.channel'
    _inherit = ['mail.channel', 'rating.mixin']

    anonymous_name = fields.Char('Anonymous Name')
    channel_type = fields.Selection(selection_add=[('livechat', 'Livechat Conversation')], ondelete={'livechat': 'cascade'})
    livechat_active = fields.Boolean('Is livechat ongoing?', help='Livechat session is active until visitor leaves the conversation.')
    livechat_channel_id = fields.Many2one('im_livechat.channel', 'Channel')
    livechat_operator_id = fields.Many2one('res.partner', string='Operator')
    chatbot_current_step_id = fields.Many2one('chatbot.script.step', string='Chatbot Current Step')
    chatbot_message_ids = fields.One2many('chatbot.message', 'mail_channel_id', string='Chatbot Messages')
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
            # add uuid to allow anonymous to listen
            if channel.channel_type == 'livechat':
                notifications.append([channel.uuid, 'mail.channel/new_message', notifications[0][2]])
        if not message.author_id:
            unpinned_members = self.channel_member_ids.filtered(lambda member: not member.is_pinned)
            if unpinned_members:
                unpinned_members.write({'is_pinned': True})
                notifications = self._channel_channel_notifications(unpinned_members.partner_id.ids) + notifications
        return notifications

    def channel_info(self):
        """ Extends the channel header by adding the livechat operator and the 'anonymous' profile
            :rtype : list(dict)
        """
        channel_infos = super().channel_info()
        channel_infos_dict = dict((c['id'], c) for c in channel_infos)
        for channel in self:
            channel_infos_dict[channel.id]['channel']['anonymous_name'] = channel.anonymous_name
            channel_infos_dict[channel.id]['channel']['anonymous_country'] = {
                'code': channel.country_id.code,
                'id': channel.country_id.id,
                'name': channel.country_id.name,
            } if channel.country_id else [('clear',)]
            if channel.livechat_operator_id:
                display_name = channel.livechat_operator_id.user_livechat_username or channel.livechat_operator_id.display_name
                channel_infos_dict[channel.id]['operator_pid'] = (channel.livechat_operator_id.id, display_name.replace(',', ''))
        return list(channel_infos_dict.values())

    @api.autovacuum
    def _gc_empty_livechat_sessions(self):
        hours = 1  # never remove empty session created within the last hour
        self.env.cr.execute("""
            SELECT id as id
            FROM mail_channel C
            WHERE NOT EXISTS (
                SELECT 1
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

    def _message_update_content_after_hook(self, message):
        self.ensure_one()
        if self.channel_type == 'livechat':
            self.env['bus.bus']._sendone(self.uuid, 'mail.message/insert', {
                'id': message.id,
                'body': message.body,
            })
        return super()._message_update_content_after_hook(message=message)

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
        mail_body = self.env['ir.qweb']._render('im_livechat.livechat_email_template', render_context, minimal_qcontext=True)
        mail_body = self.env['mail.render.mixin']._replace_local_links(mail_body)
        mail = self.env['mail.mail'].sudo().create({
            'subject': _('Conversation with %s', self.livechat_operator_id.user_livechat_username or self.livechat_operator_id.name),
            'email_from': company.catchall_formatted or company.email_formatted,
            'author_id': self.env.user.partner_id.id,
            'email_to': email,
            'body_html': mail_body,
        })
        mail.send()

    def _get_channel_history(self):
        """
        Converting message body back to plaintext for correct data formatting in HTML field.
        """
        return Markup('').join(
            Markup('%s: %s<br/>') % (message.author_id.name or self.anonymous_name, html2plaintext(message.body))
            for message in self.message_ids.sorted('id')
        )

    # =======================
    # Chatbot
    # =======================

    def _chatbot_find_customer_values_in_messages(self, step_type_to_field):
        """
        Look for user's input in the channel's messages based on a dictionary
        mapping the step_type to the field name of the model it will be used on.

        :param dict step_type_to_field: a dict of step types to customer fields
            to fill, like : {'question_email': 'email_from', 'question_phone': 'mobile'}
        """
        values = {}
        filtered_message_ids = self.chatbot_message_ids.filtered(
            lambda m: m.script_step_id.step_type in step_type_to_field.keys()
        )
        for message_id in filtered_message_ids:
            field_name = step_type_to_field[message_id.script_step_id.step_type]
            if not values.get(field_name):
                values[field_name] = html2plaintext(message_id.user_raw_answer or '')

        return values

    def _chatbot_post_message(self, chatbot_script, body):
        """ Small helper to post a message as the chatbot operator

        :param record chatbot_script
        :param string body: message HTML body """

        return self.with_context(mail_create_nosubscribe=True).message_post(
            author_id=chatbot_script.operator_partner_id.id,
            body=body,
            message_type='comment',
            subtype_xmlid='mail.mt_comment',
        )

    def _chatbot_validate_email(self, email_address, chatbot_script):
        email_address = html2plaintext(email_address)
        email_normalized = email_normalize(email_address)

        posted_message = False
        error_message = False
        if not email_normalized:
            error_message = _(
                "'%(input_email)s' does not look like a valid email. Can you please try again?",
                input_email=email_address
            )
            posted_message = self._chatbot_post_message(chatbot_script, plaintext2html(error_message))

        return {
            'success': bool(email_normalized),
            'posted_message': posted_message,
            'error_message': error_message,
        }

    def _message_post_after_hook(self, message, msg_vals):
        """
        This method is called just before _notify_thread() method which is calling the _message_format()
        method. We need a 'chatbot.message' record before it happens to correctly display the message.
        It's created only if the mail channel is linked to a chatbot step.
        """
        if self.chatbot_current_step_id:
            self.env['chatbot.message'].sudo().create({
                'mail_message_id': message.id,
                'mail_channel_id': self.id,
                'script_step_id': self.chatbot_current_step_id.id,
            })
        return super(MailChannel, self)._message_post_after_hook(message, msg_vals)

    def _chatbot_restart(self, chatbot_script):
        self.write({
            'chatbot_current_step_id': False
        })

        self.chatbot_message_ids.unlink()

        return self._chatbot_post_message(
            chatbot_script,
            '<div class="o_mail_notification">%s</div>' % _('Restarting conversation...'))
