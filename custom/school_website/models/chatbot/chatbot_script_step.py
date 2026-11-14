# -*- coding: utf-8 -*-

import re
from odoo import _, api, fields, models
from odoo.tools import email_normalize, html2plaintext


class ChatbotScriptStep(models.Model):
    _inherit = "chatbot.script.step"

    step_type = fields.Selection(
        selection_add=[("ai_chat", "AI Assistant (OpenAI / Gemini)")],
        ondelete={"ai_chat": "set default"},
    )
    is_ai_powered = fields.Boolean(
        string="Use AI for this Step",
        default=False,
        help="If enabled, free text visitor input on this step will be processed by the AI LLM.",
    )

    def _is_last_step(self, discuss_channel=False):
        self.ensure_one()
        if self.step_type == "ai_chat":
            return False
        return super()._is_last_step(discuss_channel=discuss_channel)

    def _process_answer(self, discuss_channel, message_body):
        self.ensure_one()

        # Handle question_email without crashing on free text questions
        if self.step_type == "question_email":
            clean_text = html2plaintext(message_body or "").strip()
            if not email_normalize(clean_text):
                match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_text)
                if match and email_normalize(match.group(0)):
                    message_body = match.group(0)
                elif self.chatbot_script_id.use_ai:
                    # Do not crash with ValidationError - keep the visitor on step for continuous AI assistance
                    return self

        is_ai_step = self.step_type == "ai_chat" or (
            (self.is_ai_powered or self.chatbot_script_id.use_ai)
            and self.step_type in ("free_input_single", "free_input_multi")
        )

        if is_ai_step:
            clean_text = html2plaintext(message_body or "").strip()
            if clean_text:
                ai_reply = self.chatbot_script_id._generate_ai_response(clean_text, discuss_channel)
                discuss_channel.chatbot_ai_pending_reply = ai_reply

            if self.step_type == "ai_chat":
                # Continuous AI conversation loop: stay permanently on ai_chat step
                return self

            # Check if user selected one of the step's specific answers
            user_selected_answer = discuss_channel.sudo().chatbot_message_ids.user_script_answer_id
            next_step = self._fetch_next_step(user_selected_answer)
            if next_step:
                return next_step

        return super()._process_answer(discuss_channel, message_body)

    def _process_step(self, discuss_channel):
        self.ensure_one()
        if self.step_type == "ai_chat":
            if discuss_channel.chatbot_ai_pending_reply:
                reply = discuss_channel.chatbot_ai_pending_reply
                discuss_channel.chatbot_ai_pending_reply = False
                return discuss_channel._chatbot_post_message(self.chatbot_script_id, reply)

            # First arrival at ai_chat step - post initial prompt / greeting
            greeting = self.message or _("<p>Hello! I am Harvard University's AI Assistant. How can I help you today?</p>")
            return discuss_channel._chatbot_post_message(self.chatbot_script_id, greeting)

        return super()._process_step(discuss_channel)
