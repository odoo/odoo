# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Dashboards',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Create your custom dashboard',
    'description': """
Lets the user create a custom dashboard.
========================================

Allows users to create custom dashboard.
    """,
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'board_view.xml',
        'board_mydashboard_view.xml',
        'views/board.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
