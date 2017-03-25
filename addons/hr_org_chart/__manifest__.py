# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Org Chart',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
Org Chart Widget for HR
=======================

This module extend the employee form with a organizational chart.
(N+1, N+2, direct subordinates)
        """,
    'depends': ['hr'],
    'auto_install': False,
    'data': [
        'views/hr_template.xml',
        'views/hr_views.xml'
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ]
}
