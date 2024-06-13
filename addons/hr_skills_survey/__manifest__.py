# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Skills Certification',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Add certification to resume of your employees',
    'description':
        """
Certification and Skills for HR
===============================

This module adds certification to resume for employees.
        """,
    'depends': ['hr_skills', 'survey'],
    'data': [
        'views/hr_templates.xml',
        'data/hr_resume_data.xml',
        'views/hr_employee_certification_views.xml',
        'views/survey_survey_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'hr_skills_survey/static/src/fields/**/*',
            'hr_skills_survey/static/src/xml/**/*',
        ],
    },
    'demo': [
        'data/hr_resume_demo.xml',
    ],
    'license': 'LGPL-3',
}
