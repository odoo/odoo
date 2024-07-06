from odoo import models, fields, api

class Chatbot(models.Model):
    _name = 'chatbot.model'
    _description = 'Chatbot Configuration'

    name = fields.Char(string='Name', required=True)
    api_url = fields.Char(string='API URL', required=True)
    api_key = fields.Char(string='API Key')
    model_type = fields.Selection([
        ('openai', 'OpenAI'),
        ('self_hosted', 'Self-Hosted')
    ], string='Model Type', default='openai', required=True)
    
    @api.model
    def send_message(self, message):
        if self.model_type == 'openai':
            return self._send_openai_message(message)
        elif self.model_type == 'self_hosted':
            return self._send_self_hosted_message(message)
    
    def _send_openai_message(self, message):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [{'role': 'user', 'content': message}]
        }
        response = requests.post(self.api_url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return 'Error: Could not retrieve response'
    
    def _send_self_hosted_message(self, message):
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'messages': [{'role': 'user', 'content': message}]
        }
        response = requests.post(self.api_url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return 'Error: Could not retrieve response'
