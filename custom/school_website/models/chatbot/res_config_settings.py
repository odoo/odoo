# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    chatbot_ai_enabled = fields.Boolean(
        string="Enable Livechat AI",
        config_parameter="school_website.chatbot_ai_enabled",
        default=True,
        help="Global switch to enable AI LLM responses for website chatbots.",
    )
    chatbot_ai_provider = fields.Selection(
        [
            ("openai", "OpenAI (ChatGPT)"),
            ("gemini", "Google Gemini"),
            ("openrouter", "OpenRouter (OpenRouter.ai)"),
        ],
        string="Default AI Provider",
        config_parameter="school_website.chatbot_ai_provider",
        default="openai",
        help="Default provider for Chatbot AI services.",
    )
    chatbot_ai_api_key = fields.Char(
        string="Global AI API Key",
        config_parameter="school_website.chatbot_ai_api_key",
        help="Global API Key (OpenAI sk-... or Google Gemini API key). Used by chatbots if their individual key is empty.",
    )
    chatbot_ai_model = fields.Char(
        string="Default AI Model",
        config_parameter="school_website.chatbot_ai_model",
        default="gpt-4o-mini",
        help="Default model name, e.g. gpt-4o-mini or gemini-1.5-flash.",
    )
    chatbot_ai_system_prompt = fields.Text(
        string="Default System Prompt",
        config_parameter="school_website.chatbot_ai_system_prompt",
        default=(
            "You are Harvard University's official conversational AI assistant. "
            "Help prospective students, applicants, and visitors with inquiries regarding undergraduate "
            "and graduate academic programs, admission requirements, deadlines, tuition, scholarships, "
            "campus life, and upcoming campus events. Answer concisely, politely, and authoritatively. "
            "Keep replies brief (2-4 sentences or compact bullet points) so they fit nicely into live chat."
        ),
        help="Default persona and knowledge prompt for AI chatbots.",
    )
