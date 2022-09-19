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
        'security/hr_recruitment_skills_security.xml',
        'views/hr_applicant_views.xml',
        'views/hr_applicant_skill_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
