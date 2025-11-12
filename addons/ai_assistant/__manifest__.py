# -*- coding: utf-8 -*-
{
    'name': 'AI Assistant',
    'version': '19.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Conversational AI Assistant integrated with OpenAI',
    'description': """
AI Assistant for Odoo
======================
This module provides an intelligent conversational AI assistant that integrates with OpenAI's GPT models.

Features:
---------
* Conversational interface integrated into Odoo
* Context-aware responses based on current module
* Database search and record creation capabilities
* Integration with Odoo's messaging system
* Secure API key management
* Conversation history tracking
* Multi-user support

The assistant can help users:
- Search for records
- Create and update data
- Answer questions about the system
- Provide insights and recommendations
- Automate repetitive tasks
    """,
    'author': 'AI Assistant Team',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'bus',
    ],
    'data': [
        'security/ai_assistant_security.xml',
        'security/ir.model.access.csv',
        'views/ai_config_views.xml',
        'views/ai_conversation_views.xml',
        'views/ai_assistant_menu.xml',
        'data/ai_assistant_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_assistant/static/src/js/ai_assistant_service.js',
            'ai_assistant/static/src/js/ai_chat_window.js',
            'ai_assistant/static/src/xml/ai_chat_window.xml',
            'ai_assistant/static/src/scss/ai_assistant.scss',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
