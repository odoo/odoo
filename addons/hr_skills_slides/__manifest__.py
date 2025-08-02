# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Skills e-learning',
    'category': 'Human Resources/Employees',
    'version': '1.0',
    'summary': 'Add completed courses to resume of your employees',
    'description':
        """
E-learning and Skills for HR
============================

This module add completed courses to resume for employees.
        """,
    'depends': ['hr_skills', 'website_slides'],
    'data': [
        'views/hr_employee_views.xml',
        'views/hr_employee_public_views.xml',
        'views/hr_resume_line_views.xml',
        'views/slide_channel_views.xml',
        'views/hr_views.xml',
    ],
    'demo': [
        'data/hr_resume_line_demo.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'hr_skills_slides/static/src/scss/**/*',
            'hr_skills_slides/static/src/fields/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
