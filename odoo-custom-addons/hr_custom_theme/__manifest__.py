# -*- coding: utf-8 -*-
{
    'name': 'HR Custom Theme',
    'version': '14.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Custom theme for HR Employee module',
    'description': """
        HR Custom Theme Module
        =======================
        This module provides custom styling and theming for the HR/Employee module.
        You can customize colors, fonts, and layouts for your HR portal.
    """,
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'license': 'LGPL-3',
    'depends': ['hr', 'web'],
    'data': [
        'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_custom_theme/static/src/css/hr_custom_theme.css',
        ],
        'web.assets_frontend': [
            'hr_custom_theme/static/src/css/hr_custom_theme.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
