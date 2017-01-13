# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portal',
    'version': '1.0',
    'depends': [
        'base',
        'auth_signup',
    ],
    'category': 'Extra Tools',
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
    'data': [
        'data/portal_data.xml',
        'views/portal_views.xml',
        'wizard/portal_wizard_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': ['data/portal_demo.xml'],
    'auto_install': True,
    'installable': True,
}
