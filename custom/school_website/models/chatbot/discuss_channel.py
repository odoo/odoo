# -*- coding: utf-8 -*-

from markupsafe import Markup
from odoo import _, api, fields, models
from odoo.tools import html2plaintext


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    chatbot_ai_pending_reply = fields.Html("Pending AI Reply", store=False)

    def _chatbot_validate_email(self, email_address, chatbot_script):
        """Override to support AI-driven answers when input is not an email."""
        return chatbot_script._validate_email(email_address, self)

    def _message_post_after_hook(self, message, msg_vals):
        res = super()._message_post_after_hook(message, msg_vals)
        for channel in self:
            if channel.channel_type != "livechat":
                continue

            bot_partner_id = channel.livechat_operator_id.id if channel.livechat_operator_id else False
            if not bot_partner_id:
                continue

            # Ensure message originated from the visitor, not the bot operator
            if message.author_id and message.author_id.id == bot_partner_id:
                continue

            # Don't process non-comment messages (e.g. system notifications)
            if message.message_type not in ("comment", "email"):
                continue

            # Don't process button clicks (handled by script answer branching)
            if self.env.context.get("selected_answer_id"):
                continue

            # Find if current operator is an AI-enabled chatbot
            bot_script = channel.env["chatbot.script"].sudo().search(
                [
                    ("operator_partner_id", "=", bot_partner_id),
                    ("use_ai", "=", True),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if not bot_script:
                continue

            # If channel is at a question_email or question_phone step, email/phone validation handles it
            current_step = channel.chatbot_current_step_id
            if current_step and current_step.step_type in ("question_email", "question_phone"):
                continue

            # Keep livechat conversation open and active
            if channel.livechat_end_dt:
                channel.sudo().livechat_end_dt = False

            clean_text = html2plaintext(message.body or "").strip()
            if clean_text:
                ai_reply = bot_script._generate_ai_response(clean_text, channel)
                channel._chatbot_post_message(bot_script, ai_reply)

        return res

    def _chatbot_post_message(self, chatbot_script, body):
        """Ensure rich HTML formatting (bold, lists, links) renders properly in livechat."""
        if isinstance(body, str) and ("<" in body and ">" in body):
            body = Markup(body)
        return super()._chatbot_post_message(chatbot_script, body)

    def _forward_human_operator(self, chatbot_script_step=None, users=None):
        """Override operator forward to provide AI fallback if human operators are offline."""
        res = super()._forward_human_operator(chatbot_script_step=chatbot_script_step, users=users)
        for channel in self:
            if channel.livechat_failure == "no_agent":
                bot_script = chatbot_script_step.chatbot_script_id if chatbot_script_step else False
                if bot_script and bot_script.use_ai and bot_script.ai_fallback_on_no_operator:
                    fallback_msg = _(
                        "<p>Our human admissions counselors are currently offline, but our "
                        "<strong>Harvard University AI Assistant</strong> is here to help! "
                        "Feel free to ask any question regarding admissions, degree programs, or campus life.</p>"
                    )
                    channel._chatbot_post_message(bot_script, fallback_msg)
        return res
