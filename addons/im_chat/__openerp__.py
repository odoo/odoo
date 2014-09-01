{
    'name' : 'Instant Messaging',
    'version': '1.0',
    'summary': 'OpenERP Chat',
    'author': 'OpenERP SA',
    'sequence': '18',
    'category': 'Tools',
    'complexity': 'easy',
    'description':
        """
Instant Messaging
=================

Allows users to chat with each other in real time. Find other users easily and
chat in real time. It support several chats in parallel.
        """,
    'data': [
        'security/ir.model.access.csv',
        'security/im_security.xml',
        'views/im_chat.xml',
    ],
    'depends' : ['base', 'web', 'bus'],
    'qweb': ['static/src/xml/*.xml'],
    'application': True,
}
