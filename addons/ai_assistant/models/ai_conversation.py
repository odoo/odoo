# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AIConversation(models.Model):
    """AI Assistant Conversation"""

    _name = 'ai.conversation'
    _description = 'AI Conversation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'last_message_date desc, id desc'

    name = fields.Char(string='Conversation Title', compute='_compute_name', store=True)
    user_id = fields.Many2one('res.users', string='User', required=True,
                              default=lambda self: self.env.user, index=True)
    message_ids = fields.One2many('ai.message', 'conversation_id', string='Messages')
    message_count = fields.Integer(string='Message Count', compute='_compute_message_count', store=True)

    state = fields.Selection([
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='State', default='active', tracking=True)

    context_module = fields.Char(string='Context Module',
                                  help='The Odoo module the user was in when starting this conversation')
    context_model = fields.Char(string='Context Model',
                                help='The model the user was viewing')
    context_record_id = fields.Integer(string='Context Record ID',
                                       help='The specific record ID if any')

    last_message_date = fields.Datetime(string='Last Message', compute='_compute_last_message_date', store=True)
    create_date = fields.Datetime(string='Created On', readonly=True)

    active = fields.Boolean(string='Active', default=True)

    @api.depends('message_ids', 'message_ids.content')
    def _compute_name(self):
        """Generate conversation title from first message"""
        for conversation in self:
            if conversation.message_ids:
                first_user_msg = conversation.message_ids.filtered(lambda m: m.role == 'user')
                if first_user_msg:
                    content = first_user_msg[0].content
                    # Take first 50 chars as title
                    conversation.name = content[:50] + ('...' if len(content) > 50 else '')
                else:
                    conversation.name = _('New Conversation')
            else:
                conversation.name = _('New Conversation')

    @api.depends('message_ids')
    def _compute_message_count(self):
        """Count messages in conversation"""
        for conversation in self:
            conversation.message_count = len(conversation.message_ids)

    @api.depends('message_ids', 'message_ids.create_date')
    def _compute_last_message_date(self):
        """Get date of last message"""
        for conversation in self:
            if conversation.message_ids:
                conversation.last_message_date = max(conversation.message_ids.mapped('create_date'))
            else:
                conversation.last_message_date = conversation.create_date or fields.Datetime.now()

    def send_message(self, content, context_module=None):
        """
        Send a message in this conversation and get AI response

        :param content: User message content
        :param context_module: Optional module context
        :return: AI response message record
        """
        self.ensure_one()

        if self.state == 'closed':
            raise UserError(_('This conversation is closed. Please start a new conversation.'))

        # Update context if provided
        if context_module:
            self.context_module = context_module

        # Create user message
        user_message = self.env['ai.message'].create({
            'conversation_id': self.id,
            'role': 'user',
            'content': content,
        })

        # Get AI response
        try:
            assistant_message = self._get_ai_response()
            return assistant_message

        except Exception as e:
            _logger.exception('Failed to get AI response')
            # Create error message
            error_message = self.env['ai.message'].create({
                'conversation_id': self.id,
                'role': 'assistant',
                'content': _('Sorry, I encountered an error: %s') % str(e),
                'is_error': True,
            })
            return error_message

    def _get_ai_response(self):
        """Get response from AI provider"""
        self.ensure_one()

        # Get configuration
        config = self.env['ai.config'].get_default_config()
        if not config:
            raise UserError(_('AI Assistant is not configured'))

        provider = config.provider_id

        # Prepare conversation history
        conversation_history = self._prepare_conversation_history(config)

        # Get system prompt
        system_prompt = config.get_system_prompt(self.context_module)

        # Get available tools
        tools = config.get_available_tools()

        # Send to AI provider
        response = provider.send_message(
            conversation_history=conversation_history,
            system_prompt=system_prompt,
            tools=tools if tools else None
        )

        # Handle tool calls if any
        if response.get('tool_calls'):
            return self._handle_tool_calls(response, config, provider, system_prompt, tools)

        # Create assistant message
        assistant_message = self.env['ai.message'].create({
            'conversation_id': self.id,
            'role': 'assistant',
            'content': response['content'],
            'metadata': json.dumps({
                'finish_reason': response.get('finish_reason'),
                'usage': response.get('usage', {}),
            })
        })

        return assistant_message

    def _handle_tool_calls(self, response, config, provider, system_prompt, tools):
        """Handle AI tool/function calls"""
        self.ensure_one()

        # Create assistant message with tool calls
        tool_call_message = self.env['ai.message'].create({
            'conversation_id': self.id,
            'role': 'assistant',
            'content': response.get('content', ''),
            'metadata': json.dumps({
                'tool_calls': response['tool_calls'],
                'finish_reason': response.get('finish_reason'),
            })
        })

        # Execute each tool call
        tool_results = []
        for tool_call in response['tool_calls']:
            try:
                function_name = tool_call['function']['name']
                function_args = json.loads(tool_call['function']['arguments'])

                _logger.info(f'Executing tool: {function_name} with args: {function_args}')

                result = self._execute_tool(function_name, function_args)

                tool_results.append({
                    'role': 'tool',
                    'tool_call_id': tool_call['id'],
                    'name': function_name,
                    'content': json.dumps(result)
                })

                # Log tool execution
                self.env['ai.message'].create({
                    'conversation_id': self.id,
                    'role': 'tool',
                    'content': f"Executed {function_name}: {json.dumps(result, indent=2)}",
                    'metadata': json.dumps({
                        'tool_call_id': tool_call['id'],
                        'function_name': function_name,
                        'arguments': function_args,
                    })
                })

            except Exception as e:
                _logger.exception(f'Error executing tool {function_name}')
                tool_results.append({
                    'role': 'tool',
                    'tool_call_id': tool_call['id'],
                    'name': function_name,
                    'content': json.dumps({'error': str(e)})
                })

        # Get new response with tool results
        conversation_history = self._prepare_conversation_history(config)

        # Add tool call message
        conversation_history.append({
            'role': 'assistant',
            'content': response.get('content', ''),
            'tool_calls': response['tool_calls']
        })

        # Add tool results
        conversation_history.extend(tool_results)

        # Get final response
        final_response = provider.send_message(
            conversation_history=conversation_history,
            system_prompt=system_prompt,
            tools=tools
        )

        # Create final assistant message
        final_message = self.env['ai.message'].create({
            'conversation_id': self.id,
            'role': 'assistant',
            'content': final_response['content'],
            'metadata': json.dumps({
                'finish_reason': final_response.get('finish_reason'),
                'usage': final_response.get('usage', {}),
            })
        })

        return final_message

    def _execute_tool(self, function_name, arguments):
        """Execute a tool/function call"""
        self.ensure_one()

        if function_name == 'search_records':
            return self._tool_search_records(**arguments)
        elif function_name == 'create_record':
            return self._tool_create_record(**arguments)
        elif function_name == 'update_record':
            return self._tool_update_record(**arguments)
        elif function_name == 'get_model_info':
            return self._tool_get_model_info(**arguments)
        else:
            raise UserError(_('Unknown tool: %s') % function_name)

    def _tool_search_records(self, model, domain, fields=None, limit=10):
        """Search for records in the database"""
        try:
            Model = self.env[model].with_user(self.user_id)
            records = Model.search(domain, limit=limit)

            if fields:
                result = records.read(fields)
            else:
                # Get display_name by default
                result = [{'id': r.id, 'display_name': r.display_name} for r in records]

            return {
                'success': True,
                'count': len(result),
                'records': result
            }

        except Exception as e:
            _logger.exception(f'Error searching records in {model}')
            return {
                'success': False,
                'error': str(e)
            }

    def _tool_create_record(self, model, values):
        """Create a new record"""
        try:
            Model = self.env[model].with_user(self.user_id)
            record = Model.create(values)

            return {
                'success': True,
                'id': record.id,
                'display_name': record.display_name
            }

        except Exception as e:
            _logger.exception(f'Error creating record in {model}')
            return {
                'success': False,
                'error': str(e)
            }

    def _tool_update_record(self, model, record_id, values):
        """Update an existing record"""
        try:
            Model = self.env[model].with_user(self.user_id)
            record = Model.browse(record_id)

            if not record.exists():
                return {
                    'success': False,
                    'error': f'Record {record_id} not found in {model}'
                }

            record.write(values)

            return {
                'success': True,
                'id': record.id,
                'display_name': record.display_name
            }

        except Exception as e:
            _logger.exception(f'Error updating record {record_id} in {model}')
            return {
                'success': False,
                'error': str(e)
            }

    def _tool_get_model_info(self, model):
        """Get information about a model"""
        try:
            Model = self.env[model]
            fields_info = Model.fields_get()

            return {
                'success': True,
                'model': model,
                'description': Model._description,
                'fields': {
                    name: {
                        'type': info['type'],
                        'string': info.get('string', ''),
                        'help': info.get('help', ''),
                        'required': info.get('required', False),
                    }
                    for name, info in fields_info.items()
                    if not name.startswith('__')
                }
            }

        except Exception as e:
            _logger.exception(f'Error getting model info for {model}')
            return {
                'success': False,
                'error': str(e)
            }

    def _prepare_conversation_history(self, config):
        """Prepare conversation history for AI"""
        self.ensure_one()

        max_messages = config.max_conversation_messages or 20

        # Get recent messages (excluding tool messages for simplicity)
        messages = self.message_ids.filtered(lambda m: m.role in ['user', 'assistant']).sorted('create_date')

        # Limit to max messages
        if len(messages) > max_messages:
            messages = messages[-max_messages:]

        # Convert to API format
        history = []
        for msg in messages:
            history.append({
                'role': msg.role,
                'content': msg.content or ''
            })

        return history

    def close_conversation(self):
        """Close this conversation"""
        self.write({'state': 'closed'})

    @api.model
    def close_inactive_conversations(self):
        """Cron job to close inactive conversations"""
        config = self.env['ai.config'].get_default_config()
        if not config or not config.conversation_timeout:
            return

        timeout_minutes = config.conversation_timeout
        cutoff_date = datetime.now() - timedelta(minutes=timeout_minutes)

        inactive_conversations = self.search([
            ('state', '=', 'active'),
            ('last_message_date', '<', cutoff_date)
        ])

        inactive_conversations.write({'state': 'closed'})

        _logger.info(f'Closed {len(inactive_conversations)} inactive conversations')
