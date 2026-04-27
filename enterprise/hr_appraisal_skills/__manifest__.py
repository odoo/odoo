# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Appraisal - Skills",
    'version': '1.0',
    'category': 'Human Resources/Appraisals',
    'sequence': 280,
    'summary': 'Manage skills of your employees during an appraisal process',

    'description': """
This module makes it possible to manage employee skills during an appraisal process.
    """,
    'depends': ['hr_appraisal', 'hr_skills'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_appraisal_skills_security.xml',
        'views/hr_skills_views.xml',
        'views/hr_appraisal_skill_views.xml',
        'views/hr_appraisal_skills_templates.xml',
        'report/hr_appraisal_skill_report_views.xml'
    ],
    'demo': [
        'demo/hr_appraisal_skills_demo.xml',
    ],
    'auto_install': True,
    'installable': True,
    'post_init_hook': '_populate_skills_for_confirmed',
    'assets': {
        'web.assets_backend': [
            'hr_appraisal_skills/static/src/**/*',
        ],
    },
    'license': 'OEEL-1',
}
