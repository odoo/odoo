# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Calendar Microsoft provider',
    'version': '1.0',
    'depends': ['calendar_sync', 'microsoft_account'],
    'summary': "",
    'description': """
    """,
    'category': 'Productivity/Calendar',
    'demo': [
    ],
    'data': [
        'data/calendar_provider_data.xml',
        'views/res_users_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'calendar_microsoft/static/src/js/calendar_microsoft.js',
            'calendar_microsoft/static/src/scss/calendar_microsoft.scss',
        ],
        'web.assets_qweb': [
            'calendar_microsoft/static/src/xml/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
