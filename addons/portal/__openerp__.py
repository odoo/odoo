# -*- coding: utf-8 -*-

{
    'name' : 'Portal',
    'version': '1.0',
    'depends': [
        'base',
        'share',
        'auth_signup',
    ],
    'author': 'Odoo S.A.',
    'category': 'Portal',
    'description': """
Customize access to your Odoo database to external users by creating portals.
================================================================================
A portal defines a specific user menu and access rights for its members.  This
menu can be seen by portal members, public users and any other user that
have the access to technical features (e.g. the administrator).
Also, each portal member is linked to a specific partner.

The module also associates user groups to the portal users (adding a group in
the portal automatically adds it to the portal users, etc).  That feature is
very handy when used in combination with the module 'share'.
    """,
    'website': 'https://www.odoo.com',
    'data': [
        'data/portal_data.xml',
        'views/portal_view.xml',
        'wizard/portal_wizard_view.xml',
        'wizard/share_wizard_view.xml',
        'security/ir.model.access.csv',
        'views/portal.xml',
    ],
    'demo': ['data/portal_demo.xml'],
    'auto_install': True,
    'installable': True,
}
