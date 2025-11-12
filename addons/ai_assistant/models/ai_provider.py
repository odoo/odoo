# -*- coding: utf-8 -*-

import json
import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AIProvider(models.Model):
    """OpenAI Provider integration for AI Assistant"""

    _name = 'ai.provider'
    _description = 'AI Provider'

    name = fields.Char(string='Provider Name', required=True, default='OpenAI')
    api_key = fields.Char(string='API Key', required=True)
    model_name = fields.Char(string='Model Name', required=True, default='openai/gpt-5-mini')
    api_url = fields.Char(string='API URL', default='https://api.openai.com/v1/chat/completions')
    max_tokens = fields.Integer(string='Max Tokens', default=2000)
    temperature = fields.Float(string='Temperature', default=0.7,
                               help='Controls randomness: 0 is focused, 1 is creative')
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('temperature')
    def _check_temperature(self):
        """Validate temperature is between 0 and 2"""
        for record in self:
            if not (0 <= record.temperature <= 2):
                raise ValidationError(_('Temperature must be between 0 and 2'))

    def _prepare_headers(self):
        """Prepare headers for OpenAI API request"""
        self.ensure_one()
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def _prepare_messages(self, conversation_history, system_prompt=None):
        """
        Prepare messages for OpenAI API

        :param conversation_history: List of dicts with 'role' and 'content'
        :param system_prompt: Optional system prompt to prepend
        :return: List of message dicts
        """
        messages = []

        if system_prompt:
            messages.append({
                'role': 'system',
                'content': system_prompt
            })

        messages.extend(conversation_history)

        return messages

    def _prepare_payload(self, messages, tools=None):
        """Prepare the full payload for OpenAI API"""
        self.ensure_one()

        payload = {
            'model': self.model_name,
            'messages': messages,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
        }

        # Add tools/functions if provided
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'

        return payload

    def send_message(self, conversation_history, system_prompt=None, tools=None, timeout=30):
        """
        Send a message to OpenAI API and get response

        :param conversation_history: List of message dicts
        :param system_prompt: Optional system prompt
        :param tools: Optional list of tool definitions
        :param timeout: Request timeout in seconds
        :return: Dict with response data
        """
        self.ensure_one()

        if not self.api_key:
            raise UserError(_('API Key is not configured. Please configure it in AI Assistant settings.'))

        try:
            # Prepare request
            headers = self._prepare_headers()
            messages = self._prepare_messages(conversation_history, system_prompt)
            payload = self._prepare_payload(messages, tools)

            _logger.info(f'Sending request to OpenAI API: {self.model_name}')
            _logger.debug(f'Payload: {json.dumps(payload, indent=2)}')

            # Make API request
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=timeout
            )

            # Check response status
            response.raise_for_status()

            result = response.json()
            _logger.debug(f'OpenAI response: {json.dumps(result, indent=2)}')

            return self._parse_response(result)

        except requests.exceptions.Timeout:
            _logger.error('OpenAI API request timed out')
            raise UserError(_('The AI service is taking too long to respond. Please try again.'))

        except requests.exceptions.HTTPError as e:
            _logger.error(f'OpenAI API HTTP error: {e}')
            error_message = self._parse_error(e.response)
            raise UserError(_('AI Service Error: %s') % error_message)

        except requests.exceptions.RequestException as e:
            _logger.error(f'OpenAI API request error: {e}')
            raise UserError(_('Failed to connect to AI service: %s') % str(e))

        except Exception as e:
            _logger.exception('Unexpected error in AI provider')
            raise UserError(_('An unexpected error occurred: %s') % str(e))

    def _parse_response(self, response_data):
        """
        Parse OpenAI API response

        :param response_data: Raw API response dict
        :return: Parsed response dict
        """
        try:
            choice = response_data['choices'][0]
            message = choice['message']

            result = {
                'content': message.get('content', ''),
                'role': message.get('role', 'assistant'),
                'finish_reason': choice.get('finish_reason'),
                'tool_calls': message.get('tool_calls', []),
                'usage': response_data.get('usage', {}),
            }

            return result

        except (KeyError, IndexError) as e:
            _logger.error(f'Failed to parse OpenAI response: {e}')
            raise UserError(_('Invalid response format from AI service'))

    def _parse_error(self, response):
        """Parse error from API response"""
        try:
            error_data = response.json()
            error = error_data.get('error', {})
            return error.get('message', 'Unknown error')
        except:
            return response.text or 'Unknown error'

    @api.model
    def get_default_provider(self):
        """Get the active default provider"""
        provider = self.search([('active', '=', True)], limit=1)
        if not provider:
            raise UserError(_(
                'No active AI provider configured. '
                'Please configure an AI provider in Settings > AI Assistant.'
            ))
        return provider

    def test_connection(self):
        """Test the connection to OpenAI API"""
        self.ensure_one()

        try:
            result = self.send_message(
                conversation_history=[
                    {'role': 'user', 'content': 'Hello, this is a test message.'}
                ],
                system_prompt='You are a helpful assistant. Respond briefly to test messages.'
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success!'),
                    'message': _('Connection to AI provider successful. Response: %s') % result['content'][:100],
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Failed'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
