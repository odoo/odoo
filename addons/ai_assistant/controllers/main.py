# -*- coding: utf-8 -*-

import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AIAssistantController(http.Controller):
    """Controller for AI Assistant HTTP endpoints"""

    @http.route('/ai_assistant/start_conversation', type='json', auth='user')
    def start_conversation(self, context_module=None, context_model=None, context_record_id=None):
        """
        Start a new AI conversation

        :param context_module: Current module (e.g., 'sale', 'crm')
        :param context_model: Current model (e.g., 'sale.order')
        :param context_record_id: Current record ID
        :return: Dict with conversation info
        """
        try:
            # Create new conversation
            conversation = request.env['ai.conversation'].create({
                'user_id': request.env.user.id,
                'context_module': context_module,
                'context_model': context_model,
                'context_record_id': context_record_id,
            })

            # Get welcome message
            config = request.env['ai.config'].get_default_config()
            welcome_message = config.welcome_message if config else 'Hello! How can I help you today?'

            # Create welcome message
            request.env['ai.message'].create({
                'conversation_id': conversation.id,
                'role': 'assistant',
                'content': welcome_message,
            })

            return {
                'success': True,
                'conversation_id': conversation.id,
                'conversation': self._format_conversation(conversation),
            }

        except Exception as e:
            _logger.exception('Error starting conversation')
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/ai_assistant/send_message', type='json', auth='user')
    def send_message(self, conversation_id, message, context_module=None):
        """
        Send a message in a conversation

        :param conversation_id: Conversation ID
        :param message: User message text
        :param context_module: Optional module context
        :return: Dict with assistant response
        """
        try:
            conversation = request.env['ai.conversation'].browse(conversation_id)

            if not conversation.exists():
                return {
                    'success': False,
                    'error': 'Conversation not found'
                }

            # Check access
            if conversation.user_id.id != request.env.user.id:
                return {
                    'success': False,
                    'error': 'Access denied'
                }

            # Send message and get response
            assistant_message = conversation.send_message(message, context_module)

            return {
                'success': True,
                'message': self._format_message(assistant_message),
                'conversation': self._format_conversation(conversation),
            }

        except Exception as e:
            _logger.exception('Error sending message')
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/ai_assistant/get_conversation', type='json', auth='user')
    def get_conversation(self, conversation_id):
        """
        Get conversation details with messages

        :param conversation_id: Conversation ID
        :return: Dict with conversation data
        """
        try:
            conversation = request.env['ai.conversation'].browse(conversation_id)

            if not conversation.exists():
                return {
                    'success': False,
                    'error': 'Conversation not found'
                }

            # Check access
            if conversation.user_id.id != request.env.user.id:
                return {
                    'success': False,
                    'error': 'Access denied'
                }

            return {
                'success': True,
                'conversation': self._format_conversation(conversation),
            }

        except Exception as e:
            _logger.exception('Error getting conversation')
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/ai_assistant/list_conversations', type='json', auth='user')
    def list_conversations(self, limit=10, offset=0):
        """
        List user's conversations

        :param limit: Number of conversations to return
        :param offset: Offset for pagination
        :return: Dict with conversations list
        """
        try:
            domain = [
                ('user_id', '=', request.env.user.id),
            ]

            conversations = request.env['ai.conversation'].search(
                domain,
                limit=limit,
                offset=offset,
                order='last_message_date desc'
            )

            total_count = request.env['ai.conversation'].search_count(domain)

            return {
                'success': True,
                'conversations': [self._format_conversation(c, include_messages=False) for c in conversations],
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
            }

        except Exception as e:
            _logger.exception('Error listing conversations')
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/ai_assistant/close_conversation', type='json', auth='user')
    def close_conversation(self, conversation_id):
        """
        Close a conversation

        :param conversation_id: Conversation ID
        :return: Success status
        """
        try:
            conversation = request.env['ai.conversation'].browse(conversation_id)

            if not conversation.exists():
                return {
                    'success': False,
                    'error': 'Conversation not found'
                }

            # Check access
            if conversation.user_id.id != request.env.user.id:
                return {
                    'success': False,
                    'error': 'Access denied'
                }

            conversation.close_conversation()

            return {
                'success': True,
            }

        except Exception as e:
            _logger.exception('Error closing conversation')
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/ai_assistant/get_config', type='json', auth='user')
    def get_config(self):
        """
        Get AI Assistant configuration

        :return: Configuration data
        """
        try:
            config = request.env['ai.config'].get_default_config()

            if not config:
                return {
                    'success': False,
                    'error': 'AI Assistant not configured'
                }

            return {
                'success': True,
                'config': {
                    'welcome_message': config.welcome_message,
                    'show_in_systray': config.show_in_systray,
                    'enable_database_search': config.enable_database_search,
                    'enable_record_creation': config.enable_record_creation,
                    'enable_record_update': config.enable_record_update,
                }
            }

        except Exception as e:
            _logger.exception('Error getting config')
            return {
                'success': False,
                'error': str(e)
            }

    def _format_conversation(self, conversation, include_messages=True):
        """Format conversation for JSON response"""
        data = {
            'id': conversation.id,
            'name': conversation.name,
            'state': conversation.state,
            'message_count': conversation.message_count,
            'last_message_date': conversation.last_message_date.isoformat() if conversation.last_message_date else None,
            'create_date': conversation.create_date.isoformat() if conversation.create_date else None,
            'context_module': conversation.context_module,
        }

        if include_messages:
            data['messages'] = [self._format_message(msg) for msg in conversation.message_ids]

        return data

    def _format_message(self, message):
        """Format message for JSON response"""
        return {
            'id': message.id,
            'role': message.role,
            'content': message.content,
            'is_error': message.is_error,
            'create_date': message.create_date.isoformat() if message.create_date else None,
        }
