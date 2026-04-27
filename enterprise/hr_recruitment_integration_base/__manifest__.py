# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment Integration Base',
    'version': '1.0',
    'category': 'Human Resources/Recruitment/Integration',
    'description': """
Base module for recruitment integration.
========================================
This module provides a base for the integration of recruitment with external
api from different job boards like indeed, monster, linkedin, etc.
    """,
    'depends': [
        'hr_recruitment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/hr_job_post_views.xml',
        'views/hr_job_views.xml',
        'views/hr_recruitment_platform_views.xml',
        'wizard/hr_recruitment_post_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_recruitment_integration_base/static/src/**/*.js',
            'hr_recruitment_integration_base/static/src/**/*.xml',
            'hr_recruitment_integration_base/static/src/**/*.scss',
        ]
    },
    'license': 'OEEL-1',
}
