# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Time Off in Depending on Works',
    'version': '1.0',
    'category': 'Human Resources/Time Off',
    'sequence': 95,
    'summary': 'Manage Work Entry Time Off',
    'description': """
Manage Time Off with Work Entry
===============================

This application allows you to integrate time off with work entry.
    """,
    'depends': ['hr_work_entry', 'hr_holidays'],
    'data': [
        'views/hr_leave_views.xml',
    ],
    'demo': ['data/hr_work_entry_holidays_demo.xml'],
    'installable': True,
    'application': False,
    'auto_install': True,
    'post_init_hook': '_validate_existing_work_entry',
}
