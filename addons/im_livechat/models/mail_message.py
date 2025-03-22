# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def _message_format(self, fnames, format_reply=True, legacy=False):
        """Override to remove email_from and to return the livechat username if applicable.
        A third param is added to the author_id tuple in this case to be able to differentiate it
        from the normal name in client code.

        In addition, if we are currently running a chatbot.script, we include the information about
        the chatbot.message related to this mail.message.
        This allows the frontend display to include the additional features
        (e.g: Show additional buttons with the available answers for this step). """

        vals_list = super()._message_format(fnames=fnames, format_reply=format_reply, legacy=legacy)
        for vals in vals_list:
            message_sudo = self.browse(vals['id']).sudo().with_prefetch(self.ids)
            mail_channel = self.env['mail.channel'].browse(message_sudo.res_id) if message_sudo.model == 'mail.channel' else self.env['mail.channel']
            if mail_channel.channel_type == 'livechat':
                if message_sudo.author_id:
                    vals.pop('email_from')
                if message_sudo.author_id.user_livechat_username:
                    vals['author'] = {
                        'id': message_sudo.author_id.id,
                        'user_livechat_username': message_sudo.author_id.user_livechat_username,
                    }
                # sudo: chatbot.script.step - members of a channel can access the current chatbot step
                if mail_channel.chatbot_current_step_id \
                        and message_sudo.author_id == mail_channel.chatbot_current_step_id.sudo().chatbot_script_id.operator_partner_id:
                    chatbot_message_id = self.env['chatbot.message'].sudo().search([
                        ('mail_message_id', '=', message_sudo.id)], limit=1)
                    if chatbot_message_id.script_step_id:
                        vals['chatbot_script_step_id'] = chatbot_message_id.script_step_id.id
                        if chatbot_message_id.script_step_id.step_type == 'question_selection':
                            vals['chatbot_step_answers'] = [{
                                'id': answer.id,
                                'label': answer.name,
                                'redirect_link': answer.redirect_link,
                            } for answer in chatbot_message_id.script_step_id.answer_ids]
                    if chatbot_message_id.user_script_answer_id:
                        vals['chatbot_selected_answer_id'] = chatbot_message_id.user_script_answer_id.id
        return vals_list
