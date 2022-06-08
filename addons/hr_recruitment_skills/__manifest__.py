# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment - Skills Management',
    'category': 'Human Resources/Recruitment',
    'sequence': 270,
    'version': '1.0',
    'summary': 'Manage skills of your employees',
    'description': """""",
    'depends': ['hr_skills', 'hr_recruitment'],
    'data': [
        'views/hr_applicant_views.xml',
        'views/hr_applicant_skill_views.xml',
        'security/ir.model.access.csv',
        'wizard/hr_recruitment_populate_wizard_views.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'hr_recruitment_skills/static/src/**/*.js',
        ],
        'web.assets_qweb': [
            'hr_recruitment_skills/static/src/xml/**/*',
            'hr_recruitment_skills/static/src/**/*.xml',
        ],
    },
    'license': 'LGPL-3',
}
