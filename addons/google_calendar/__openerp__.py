# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Google Calendar',
    'version': '1.0',
    'category': 'Tools',
    'description': """
The module adds the possibility to synchronize Google Calendar with Odoo
===========================================================================
""",
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['google_account', 'calendar'],
    'data': [
        'res_config_view.xml',
        'security/ir.model.access.csv',
        'views/google_calendar.xml',
        'views/res_users.xml',
        'google_calendar.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
