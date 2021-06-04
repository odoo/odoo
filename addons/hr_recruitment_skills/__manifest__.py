# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment - Skills',
    'version': '1.0',
    'category': 'Human Resources/Recruitment',
    'sequence': 90,
    'summary': 'Manage applicant skills',
    'description': "Allows to manage skills of applicants, and populate job position based upon it.",
    'depends': [
        'hr_recruitment',
        'hr_skills',
    ],
    'data': [
        'views/hr_applicant_views.xml',
        'views/hr_job_views.xml',
    ],
    'demo': [
        'data/hr_recruitment_skills_demo.xml',
    ],
    'auto_install': True,
    'application': False,
}
