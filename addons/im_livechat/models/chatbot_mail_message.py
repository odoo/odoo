# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ChatbotMailMessage(models.Model):
    _name = 'im_livechat.chatbot.mail.message'
    _description = 'Chatbot Mail Message'

    mail_message_id = fields.Many2one('mail.message', string='Related Mail Message', required=True)
    mail_channel_id = fields.Many2one('mail.channel', string='Related Mail Channel', required=True)
    chatbot_step_id = fields.Many2one('im_livechat.chatbot.script_step', string='Chatbot Step', required=True)
    user_answer_id = fields.Many2one('im_livechat.chatbot.script_question_answer', string='User\'s answer')
