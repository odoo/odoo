# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    parent_author_name = fields.Char(compute="_compute_parent_author_name")
    parent_body = fields.Html(compute="_compute_parent_body")

    @api.depends('parent_id')
    def _compute_parent_author_name(self):
        for message in self:
            author = message.parent_id.author_id or message.parent_id.author_guest_id
            message.parent_author_name = author.name if author else False

    @api.depends('parent_id.body')
    def _compute_parent_body(self):
        for message in self:
            message.parent_body = message.parent_id.body if message.parent_id else False

    def _message_format(self, format_reply=True, msg_vals=None):
        """Override to remove email_from and to return the livechat username if applicable.
        A third param is added to the author_id tuple in this case to be able to differentiate it
        from the normal name in client code.

        In addition, if we are currently running a chatbot.script, we include the information about
        the chatbot.message related to this mail.message.
        This allows the frontend display to include the additional features
        (e.g: Show additional buttons with the available answers for this step). """

        vals_list = super()._message_format(format_reply=format_reply, msg_vals=msg_vals)
        for vals in vals_list:
            message_sudo = self.browse(vals['id']).sudo().with_prefetch(self.ids)
            discuss_channel = self.env['discuss.channel'].browse(message_sudo.res_id) if message_sudo.model == 'discuss.channel' else self.env['discuss.channel']
            if discuss_channel.channel_type == 'livechat':
                if message_sudo.author_id:
                    vals.pop('email_from')
                if message_sudo.author_id.user_livechat_username:
                    del vals['author']['name']
                    vals['author']['user_livechat_username'] = message_sudo.author_id.user_livechat_username
                # sudo: chatbot.script.step - checking whether the current message is from chatbot
                if discuss_channel.chatbot_current_step_id \
                        and message_sudo.author_id == discuss_channel.chatbot_current_step_id.sudo().chatbot_script_id.operator_partner_id:
                    chatbot_message_id = self.env['chatbot.message'].sudo().search([
                        ('mail_message_id', '=', message_sudo.id)], limit=1)
                    if chatbot_message_id.script_step_id:
                        vals['chatbotStep'] = {
                            'message': {'id': message_sudo.id},
                            'scriptStep': {'id': chatbot_message_id.script_step_id.id},
                            'chatbot': {
                                'script': {'id': chatbot_message_id.script_step_id.chatbot_script_id.id},
                                'thread': {'id': discuss_channel.id, 'model': 'discuss.channel'}
                            },
                            'selectedAnswer': {'id': chatbot_message_id.user_script_answer_id.id} if chatbot_message_id.user_script_answer_id else False,
                            'operatorFound': discuss_channel.chatbot_current_step_id.step_type == 'forward_operator' and len(discuss_channel.channel_member_ids) > 2,
                        }
        return vals_list
