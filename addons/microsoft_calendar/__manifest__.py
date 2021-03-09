# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Outlook Calendar',
    'version': '1.0',
    'category': 'Productivity',
    'description': "",
    'depends': ['microsoft_account', 'calendar'],
    'qweb': ['static/src/xml/*.xml'],
    'data': [
        'data/microsoft_calendar_data.xml',
        'security/ir.model.access.csv',
        'wizard/reset_account_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/microsoft_calendar_views.xml',
        'views/microsoft_calendar_templates.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'init_initiating_microsoft_uuid',
}
