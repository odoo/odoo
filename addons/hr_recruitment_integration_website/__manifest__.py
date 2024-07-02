
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment Integration website',
    'version': '1.0',
    'category': 'Human Resources/Recruitment/Integration',
    'summary': 'Manage Job board integrations with website',
    'description': "This module allows to adapt job board integrations with online recruitment.",
    'depends': ['hr_recruitment_integration_base', 'website_hr_recruitment'],
    'auto_install': True,
    'data': [
        'wizard/hr_recruitment_post_job_views.xml'
    ],
    'license': 'LGPL-3',
}
