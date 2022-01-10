# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ChatbotScriptStep(models.Model):
    _name = 'im_livechat.chatbot.script_step'
    _description = 'Chatbot Script Step'
    _order = 'sequence'

    message = fields.Text(string='Message')
    sequence = fields.Integer(string='Sequence')
    chatbot_id = fields.Many2one(
        'im_livechat.chatbot.script', string='Chatbot', required=True, ondelete='cascade')
    type = fields.Selection([
        ('text', 'Text'),
        ('question_selection', 'Question'),
        # TODO PKO: Put the following two in website_livechat
        ('question_email', 'Email'),
        ('question_phone', 'Phone'),
    ])
    answer_ids = fields.One2many(
        'im_livechat.chatbot.script_question_answer', 'step_id', string='Answers')
    triggering_answer_ids = fields.Many2many(
        'im_livechat.chatbot.script_question_answer', 'chatbot_script_chatbot_script_question_answer_rel',
        'chatbot_script_step_id', 'chatbot_script_question_answer_id',
        string='Only If', help='Show this step only if all of these answers have been selected.')

    def _process_next_step(self, selected_answer_ids):
        self.ensure_one()
        domain = [('sequence', '>', self.sequence)]
        if selected_answer_ids:
            domain = expression.AND([domain, [
                '|',
                ('triggering_answer_ids', '=', False),
                ('triggering_answer_ids', 'in', selected_answer_ids.ids)]])
        return self.env['im_livechat.chatbot.script_step'].sudo().search(domain, limit=1)

    def _process_answer(self, mail_channel, message_content):
        """
        Process user's answer depending on the step type.

        :param mail_channel:
        :param message_content:
        :return: script step to display next
        :rtype: 'im_livechat.chatbot.script_step'
        """
        self.ensure_one()

        if self.type == 'question_selection':
            # Update 'chatbot.mail.message' with the user's answer
            user_answer_id = self.answer_ids.filtered(lambda a: a.name == message_content)
            if not user_answer_id:
                raise ValidationError(_('"%s" is not a valid answer for this step', message_content))
            mail_message_id = self.env['im_livechat.chatbot.mail.message'].search([
                ('mail_channel_id', '=', mail_channel.id),
                ('chatbot_step_id', '=', self.id)], limit=1)
            mail_message_id.write({'user_answer_id': user_answer_id.id})

        selected_answer_ids = mail_channel.livechat_chatbot_message_ids.mapped('user_answer_id')

        return self._process_next_step(selected_answer_ids)
