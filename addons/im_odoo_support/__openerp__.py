{
    'name' : 'Odoo Live Support',
    'version': '1.0',
    'summary': 'Chat with the Odoo collaborators',
    'category': 'Tools',
    'complexity': 'medium',
    'description':
        """
Odoo Live Support
=================

Ask your functional question directly to the Odoo Operators with the livechat support.

        """,
    'data': [
        "views/im_odoo_support.xml"
    ],
    'depends' : ["web", "mail"],
    'installable': True,
    'auto_install': True,
    'application': False,
}
