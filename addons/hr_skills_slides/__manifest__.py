# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Skills e-learning',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Add completed courses to resumé of your employees',
    'description':
        """
E-learning and Skills for HR
============================

This module add completed courses to resumé for employees.
        """,
    'depends': ['hr_skills', 'website_slides'],
    'data': [
        'views/hr_employee_views.xml',
        'views/hr_templates.xml',
        'data/hr_resume_data.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'hr_skills_slides/static/src/scss/**/*',
            'hr_skills_slides/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
