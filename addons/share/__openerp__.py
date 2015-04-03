# -*- coding: utf-8 -*-


{
    'name' : 'Share any Document',
    'version' : '2.0',
    'depends' : ['base', 'mail'],
    'author' : 'Odoo S.A.',
    'category': 'Tools',
    'description': """
This module adds generic sharing tools to your current Odoo database.
========================================================================

It specifically adds a 'share' button that is available in the Web client to
share any kind of Odoo data with colleagues, customers, friends.

The system will work by creating new users and groups on the fly, and by
combining the appropriate access rights and ir.rules to ensure that the shared
users only have access to the data that has been shared with them.

This is extremely useful for collaborative work, knowledge sharing,
synchronization with other companies.
    """,
    'website': 'https://www.odoo.com',
    'data': [
        'security/share_security.xml',
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'wizard/share_wizard_views.xml',
        'views/share_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'web': True,
    'qweb' : ['static/src/xml/*.xml'],
}
