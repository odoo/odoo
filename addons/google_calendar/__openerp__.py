# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Google Calendar',
    'category': 'Tools',
    'description': """
The module adds the possibility to synchronize Google Calendar with Odoo
===========================================================================
""",
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['google_account', 'calendar'],
    'qweb': ['static/src/xml/*.xml'],
    'data': [
        'data/google_calendar_data.xml',
        'views/res_config_views.xml',
        'views/google_calendar_templates.xml',
        'views/res_users_views.xml',
        'security/ir.model.access.csv',
    ],
}
