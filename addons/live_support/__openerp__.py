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
        "security/ir.model.access.csv",
        "security/live_support_security.xml",
        "live_support_view.xml",
    ],
    'depends' : ["web_im", "mail", "portal_anonymous"],
    'installable': True,
    'auto_install': False,
}
