# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.tools import is_html_empty, plaintext2html
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class LivechatChatbotScriptController(http.Controller):
    @http.route("/chatbot/restart", type="json", auth="public")
    @add_guest_to_context
    def chatbot_restart(self, channel_id, chatbot_script_id):
        discuss_channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        chatbot = request.env['chatbot.script'].browse(chatbot_script_id)
        if not discuss_channel or not chatbot.exists():
            return None
        chatbot_language = self._get_chatbot_language()
        return discuss_channel.with_context(lang=chatbot_language)._chatbot_restart(chatbot).message_format()[0]

    @http.route("/chatbot/answer/save", type="json", auth="public")
    @add_guest_to_context
    def chatbot_save_answer(self, channel_id, message_id, selected_answer_id):
        discuss_channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        chatbot_message = request.env['chatbot.message'].sudo().search([
            ('mail_message_id', '=', message_id),
            ('discuss_channel_id', '=', discuss_channel.id),
        ], limit=1)
        selected_answer = request.env['chatbot.script.answer'].sudo().browse(selected_answer_id)

        if not discuss_channel or not chatbot_message or not selected_answer.exists():
            return

        if selected_answer in chatbot_message.script_step_id.answer_ids:
            chatbot_message.write({'user_script_answer_id': selected_answer_id})

    @http.route("/chatbot/step/trigger", type="json", auth="public")
    @add_guest_to_context
    def chatbot_trigger_step(self, channel_id, chatbot_script_id=None):
        chatbot_language = self._get_chatbot_language()
        discuss_channel = request.env["discuss.channel"].with_context(lang=chatbot_language).search([("id", "=", channel_id)])
        if not discuss_channel:
            return None

        next_step = False
        # sudo: chatbot.script.step - visitor can access current step of the script
        if current_step := discuss_channel.sudo().chatbot_current_step_id:
            chatbot = current_step.chatbot_script_id
            user_messages = discuss_channel.message_ids.filtered(
                lambda message: message.author_id != chatbot.operator_partner_id
            )
            user_answer = request.env['mail.message'].sudo()
            if user_messages:
                user_answer = user_messages.sorted(lambda message: message.id)[-1]
            next_step = current_step._process_answer(discuss_channel, user_answer.body)
        elif chatbot_script_id:  # when restarting, we don't have a "current step" -> set "next" as first step of the script
            chatbot = request.env['chatbot.script'].sudo().browse(chatbot_script_id).with_context(lang=chatbot_language)
            if chatbot.exists():
                next_step = chatbot.script_step_ids[:1]

        if not next_step:
            return None

        posted_message = next_step._process_step(discuss_channel)
        return {
            'scriptStep': {
                'id': next_step.id,
                'answers': [{
                    'id': answer.id,
                    'label': answer.name,
                    'redirectLink': answer.redirect_link,
                } for answer in next_step.answer_ids],
                'isLast': next_step._is_last_step(discuss_channel),
                'message': plaintext2html(next_step.message) if not is_html_empty(next_step.message) else False,
                'type': next_step.step_type,
            },
            'message': posted_message.message_format()[0] if posted_message else None,
            'operatorFound': next_step.step_type == 'forward_operator' and len(
                discuss_channel.channel_member_ids) > 2,
        }

    @http.route("/chatbot/step/validate_email", type="json", auth="public")
    @add_guest_to_context
    def chatbot_validate_email(self, channel_id):
        discuss_channel = request.env["discuss.channel"].search(
            [("id", "=", channel_id)]
        ).with_context(lang=self._get_chatbot_language())
        if not discuss_channel or not discuss_channel.chatbot_current_step_id:
            return None

        # sudo: chatbot.script - visitor can access chatbot script of their channel
        chatbot = discuss_channel.sudo().chatbot_current_step_id.chatbot_script_id
        user_messages = discuss_channel.message_ids.filtered(
            lambda message: message.author_id != chatbot.operator_partner_id
        )

        if user_messages:
            user_answer = user_messages.sorted(lambda message: message.id)[-1]
            result = chatbot._validate_email(user_answer.body, discuss_channel)

            if result['posted_message']:
                result['posted_message'] = result['posted_message'].message_format()[0]

        return result

    def _get_chatbot_language(self):
        return request.env["chatbot.script"]._get_chatbot_language()
