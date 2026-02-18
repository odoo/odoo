# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AIConfig(models.Model):
    """Configuration for AI Assistant"""

    _name = 'ai.config'
    _description = 'AI Assistant Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Configuration Name', required=True, default='AI Assistant Configuration')
    provider_id = fields.Many2one('ai.provider', string='AI Provider', required=True,
                                   tracking=True)

    # System prompts
    default_system_prompt = fields.Text(
        string='Default System Prompt',
        default=lambda self: self._default_system_prompt(),
        tracking=True,
        help='The default system prompt used for all conversations'
    )

    # Module-specific prompts
    sales_prompt = fields.Text(
        string='Sales Module Prompt',
        help='Additional context when user is in Sales module'
    )
    crm_prompt = fields.Text(
        string='CRM Module Prompt',
        help='Additional context when user is in CRM module'
    )
    accounting_prompt = fields.Text(
        string='Accounting Module Prompt',
        help='Additional context when user is in Accounting module'
    )
    inventory_prompt = fields.Text(
        string='Inventory Module Prompt',
        help='Additional context when user is in Inventory module'
    )

    # Features
    enable_database_search = fields.Boolean(
        string='Enable Database Search',
        default=True,
        tracking=True,
        help='Allow the AI to search the database for information'
    )
    enable_record_creation = fields.Boolean(
        string='Enable Record Creation',
        default=False,
        tracking=True,
        help='Allow the AI to create records in the database'
    )
    enable_record_update = fields.Boolean(
        string='Enable Record Updates',
        default=False,
        tracking=True,
        help='Allow the AI to update existing records'
    )

    # Limits
    max_conversation_messages = fields.Integer(
        string='Max Messages in History',
        default=20,
        help='Maximum number of messages to keep in conversation history for context'
    )
    conversation_timeout = fields.Integer(
        string='Conversation Timeout (minutes)',
        default=30,
        help='Automatically close conversations after this many minutes of inactivity'
    )

    # UI Settings
    welcome_message = fields.Text(
        string='Welcome Message',
        default='Hello! I am your AI assistant. How can I help you today?',
        help='The first message shown when starting a conversation'
    )
    show_in_systray = fields.Boolean(
        string='Show in System Tray',
        default=True,
        help='Show AI Assistant icon in the system tray'
    )

    active = fields.Boolean(string='Active', default=True)

    @api.model
    def _default_system_prompt(self):
        """Default system prompt for the AI assistant"""
        return """You are an intelligent AI assistant integrated into Odoo ERP system.

Your role is to help users with their tasks by:
- Answering questions about the system and their data
- Searching for records and information in the database
- Providing insights and recommendations
- Helping with data entry and updates when authorized

Important guidelines:
1. Always be helpful, professional, and accurate
2. When you don't know something, admit it rather than guessing
3. When searching the database, explain what you're looking for
4. Before creating or modifying records, confirm with the user
5. Respect user permissions - only access data they can access
6. Provide clear, concise responses
7. When showing data, format it clearly (use lists, tables when appropriate)
8. If a task requires multiple steps, break it down clearly

You have access to various tools to help users. Use them wisely and always explain what you're doing."""

    @api.model
    def get_default_config(self):
        """Get or create the default configuration"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            # Create default config
            provider = self.env['ai.provider'].search([('active', '=', True)], limit=1)
            if provider:
                config = self.create({
                    'name': 'Default AI Configuration',
                    'provider_id': provider.id,
                })
        return config

    def get_system_prompt(self, context_module=None):
        """
        Get the appropriate system prompt based on context

        :param context_module: The module the user is currently in (e.g., 'sale', 'crm')
        :return: Complete system prompt
        """
        self.ensure_one()

        prompt = self.default_system_prompt or ''

        # Add module-specific context
        if context_module:
            module_prompts = {
                'sale': self.sales_prompt,
                'crm': self.crm_prompt,
                'account': self.accounting_prompt,
                'stock': self.inventory_prompt,
            }

            additional_prompt = module_prompts.get(context_module)
            if additional_prompt:
                prompt += f'\n\nCurrent Context: You are helping the user in the {context_module.upper()} module.\n{additional_prompt}'

        # Add capability information
        capabilities = []
        if self.enable_database_search:
            capabilities.append('- Search and retrieve data from the database')
        if self.enable_record_creation:
            capabilities.append('- Create new records')
        if self.enable_record_update:
            capabilities.append('- Update existing records')

        if capabilities:
            prompt += '\n\nYour current capabilities:\n' + '\n'.join(capabilities)

        return prompt

    def get_available_tools(self):
        """
        Get list of available tools based on configuration

        :return: List of tool definitions for OpenAI function calling
        """
        self.ensure_one()

        tools = []

        if self.enable_database_search:
            tools.append({
                'type': 'function',
                'function': {
                    'name': 'search_records',
                    'description': 'Search for records in the Odoo database',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'model': {
                                'type': 'string',
                                'description': 'The Odoo model to search (e.g., "res.partner", "sale.order")',
                            },
                            'domain': {
                                'type': 'array',
                                'description': 'Odoo domain filter as array of tuples',
                                'items': {
                                    'type': 'array'
                                }
                            },
                            'fields': {
                                'type': 'array',
                                'description': 'List of fields to retrieve',
                                'items': {
                                    'type': 'string'
                                }
                            },
                            'limit': {
                                'type': 'integer',
                                'description': 'Maximum number of records to return',
                                'default': 10
                            }
                        },
                        'required': ['model', 'domain']
                    }
                }
            })

        if self.enable_record_creation:
            tools.append({
                'type': 'function',
                'function': {
                    'name': 'create_record',
                    'description': 'Create a new record in the Odoo database',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'model': {
                                'type': 'string',
                                'description': 'The Odoo model to create (e.g., "res.partner", "sale.order")',
                            },
                            'values': {
                                'type': 'object',
                                'description': 'Dictionary of field values for the new record',
                            }
                        },
                        'required': ['model', 'values']
                    }
                }
            })

        if self.enable_record_update:
            tools.append({
                'type': 'function',
                'function': {
                    'name': 'update_record',
                    'description': 'Update an existing record in the Odoo database',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'model': {
                                'type': 'string',
                                'description': 'The Odoo model (e.g., "res.partner", "sale.order")',
                            },
                            'record_id': {
                                'type': 'integer',
                                'description': 'The ID of the record to update',
                            },
                            'values': {
                                'type': 'object',
                                'description': 'Dictionary of field values to update',
                            }
                        },
                        'required': ['model', 'record_id', 'values']
                    }
                }
            })

        # Always include this tool for getting model information
        tools.append({
            'type': 'function',
            'function': {
                'name': 'get_model_info',
                'description': 'Get information about an Odoo model (fields, description)',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'model': {
                            'type': 'string',
                            'description': 'The Odoo model name (e.g., "res.partner", "sale.order")',
                        }
                    },
                    'required': ['model']
                }
            }
        })

        return tools
