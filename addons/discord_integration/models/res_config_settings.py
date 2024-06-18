# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    discord_bot_url = fields.Char(string="Discord bot url", config_parameter='discuss.discord_bot_url')
    discord_bot_key = fields.Char(string="Discord bot key", config_parameter='discuss.discord_bot_key')
