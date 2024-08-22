# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'HR Recruitment Job Board Integration Base Module',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Job board integrations
==========================
This Module serves as a basis to Job board integrations to enable :
- Automatic Job posting 
- Applicant tracking
    """,
    'depends': ['hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/hr_recruitment_post_job_views.xml',
        'views/hr_job_views.xml',
        'views/hr_job_post_views.xml'
    ],
    'license': 'LGPL-3',
}
