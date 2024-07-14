# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment Reporting',
    'version': '1.0',
    'category': 'Human Resources/Recruitment',
    'description': """
Add a dynamic report about recruitment.
    """,
    'website': 'https://www.odoo.com/app/recruitment',
    'depends': ['hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_recruitment_reports_security.xml',
        'report/hr_recruitment_report_views.xml',
        'report/hr_recruitment_stage_report_views.xml',
    ],
    'demo': [
        'data/hr_recruitment_reports_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_recruitment_reports/static/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'hr_recruitment_reports/static/src/components/*',
            'hr_recruitment_reports/static/src/js/*',
            'hr_recruitment_reports/static/src/components/*',
        ],
    },
}
