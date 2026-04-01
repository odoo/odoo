# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ChatbotMessage(models.Model):
    """ Chatbot Mail Message
        We create a new model to store the related step to a mail.message and the user's answer.
        We do this in a new model to avoid bloating the 'mail.message' model.
    """

    _name = 'chatbot.message'
    _description = 'Chatbot Message'
    _order = 'create_date desc, id desc'
    _rec_name = 'discuss_channel_id'

    mail_message_id = fields.Many2one('mail.message', string='Related Mail Message')
    discuss_channel_id = fields.Many2one('discuss.channel', string='Discussion Channel', required=True, index=True, ondelete="cascade")
    script_step_id = fields.Many2one(
        "chatbot.script.step", string="Chatbot Step", index="btree_not_null")
    user_script_answer_id = fields.Many2one('chatbot.script.answer', string="User's answer", ondelete="set null")
    user_raw_script_answer_id = fields.Integer(help="Id of the script answer. Useful for statistics when answer is deleted.")
    user_raw_answer = fields.Html(string="User's raw answer")

    _unique_mail_message_id = models.Constraint(
        'unique (mail_message_id)',
        'A mail.message can only be linked to a single chatbot message',
    )
    _channel_id_user_raw_script_answer_id_idx = models.Index(
        "(discuss_channel_id, user_raw_script_answer_id) WHERE user_raw_script_answer_id IS NOT NULL",
    )
