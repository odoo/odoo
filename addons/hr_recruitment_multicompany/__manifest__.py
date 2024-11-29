# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment - multi company fix',
    'author': 'Odoo',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Recruitment
========================================
This module is only temporary for its purpose is to modify fields in a stable version (18.0) to make multicompany behaviour work.
    """,
    'depends': ['hr_recruitment', 'hr_recruitment_skills'],
    'data': [
        'views/hr_candidate_views.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}
