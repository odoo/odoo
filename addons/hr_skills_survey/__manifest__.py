# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Skills Certification',
    'category': 'Human Resources/Employees',
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
        'data/hr_resume_data.xml',
        'views/hr_templates.xml',
        'views/survey_survey_views.xml',
    ],
    'auto_install': True,
    'demo': [
        'data/hr_resume_demo.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
