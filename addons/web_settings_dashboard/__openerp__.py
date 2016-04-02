# -*- coding: utf-8 -*-
{
    'name': 'Odoo Settings Dashboard',
    'version': '1.0',
    'summary': 'Quick actions for installing new app, adding users, completing planners, etc.',
    'category': 'Tools',
    'description':
    """
Odoo dashboard
==============
* Quick access to install apps
* Quick users add
* Access all planners at one place
* Quick access to the `App Store` and `Theme Store`

        """,
    'data': [
        'views/dashboard_views.xml',
        'views/dashboard_templates.xml',
    ],
    'depends': ['web_planner'],
    'qweb': ['static/src/xml/dashboard.xml'],
    'auto_install': True,
}
