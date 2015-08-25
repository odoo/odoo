# -*- coding: utf-8 -*-
{
    'name' : 'Instant Messaging',
    'version': '1.0',
    'summary': 'Chat between users',
    'sequence': 115,
    'category': 'Tools',
    'complexity': 'easy',
    'website': 'https://www.odoo.com/page/live-chat',
    'description':
        """
Instant Messaging
=================
Allows users to chat with each other in real time. Find other users easily and
chat in real time. It support several chats in parallel.
        """,
    'data': [
        'security/ir.model.access.csv',
        'security/im_chat_session_security.xml',
        'views/im_chat_session_templates.xml',
        'views/im_chat_session_views.xml',
        'data/im_chat_session_data.xml',
        ],
    'depends': ['base', 'web', 'bus'],
    'qweb': ['static/src/xml/*.xml'],
    'application': True,
    'installable': True,
}
