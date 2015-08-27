# -*- coding: utf-8 -*-
{
    'name': 'Odoo Dashboard',
    'version': '1.0',
    'summary': 'Quick actions for installing new app, user invitation, planners',
    'author': 'Odoo SA',
    'category': 'Tools',
    'description':
    """
Odoo dashboard
==============
* Quick access to install apps
* Quick users invite
* Access all planners at one place
* Quick access to the `App Store` and `Theme Store`

        """,
    'data': [
        'views/dashboard_views.xml',
        'views/dashboard_templates.xml',
    ],
    'depends': ['auth_signup', 'web_planner'],
    'qweb': ['static/src/xml/dashboard.xml'],
    'auto_install': True,
}
