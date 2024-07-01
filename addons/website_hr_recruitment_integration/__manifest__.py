# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Job board website integration',
    'category': 'Website/Website',
    'version': '1.0',
    'summary': 'Manage Job board integrations with website',
    'description': "This module allows to adapt job board integrations with online recruitment.",
    'depends': ['hr_recruitment_integration', 'website_hr_recruitment'],
    'auto_install': ['hr_recruitment_integration', 'website_hr_recruitment'],
    'data': [
        'wizard/hr_recruitment_post_job_views.xml'
    ],
    'license': 'LGPL-3',
}
