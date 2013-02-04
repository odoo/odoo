{
    'name' : 'Live Support',
    'version': '1.0',
    'category': 'Tools',
    'complexity': 'easy',
    'description':
        """
OpenERP Live Support
====================
Allow to drop instant messaging widgets on any web page that will communicate with the current
server.
        """,
    'data': [
    ],
    'depends' : ["web_im", "mail", "portal_anonymous"],
    'installable': True,
    'auto_install': False,
}
