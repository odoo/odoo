# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
import json

class TelegramBot(models.Model):
    _name = 'telegram.bot'
    _description = 'Telegram Bot Configuration'

    name = fields.Char(string="Bot Name", required=True)
    bot_token =  ""

    def send_telegram_message(self, chat_id, message):
        """Send a message to a Telegram user."""
        if not self.bot_token:
            return {'error': 'No bot token configured'}
        
        url = f'https://api.telegram.org/bot{self.bot_token}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        headers = {
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                url, 
                data=json.dumps(payload),
                headers=headers,
                timeout=10
            )
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}