# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment Integration website',
    'version': '1.0',
    'category': 'Human Resources/Recruitment/Integration',
    'summary': 'Manage Job board integrations with website',
    'description': """
This module allows to adapt job board integrations with online recruitment by
providing an AI to transform your website job offers into attractive job
descriptions that will attract potential candidates.
""",
    'depends': [
        'hr_recruitment_integration_base',
        'website_hr_recruitment',
    ],
    'auto_install': True,
    'data': [
        'wizard/hr_recruitment_post_views.xml'
    ],
    'license': 'OEEL-1',
}
