# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Skills Certification',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Add certification to resumé of your employees',
    'description':
        """
Certification and Skills for HR
===============================

This module adds certification to resumé for employees.
        """,
    'depends': ['hr_skills', 'survey'],
    'data': [
        'views/hr_templates.xml',
        'data/hr_resume_data.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_qweb': [
            'hr_skills_survey/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
