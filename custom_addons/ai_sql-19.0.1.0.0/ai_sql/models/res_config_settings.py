# -*- coding: utf-8 -*-
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    user_openai_api_key = fields.Char( # Name it consistently now it's always the user's
        string="OpenAI API Key",
        config_parameter='niyu_odoo_ai.user_openai_api_key', # Unique config param
        password=True,
        help="Your organization's OpenAI API key for SQL generation and processing."
    )