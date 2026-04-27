# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment Integration Skills Monster',
    'version': '1.0',
    'category': 'Human Resources/Recruitment/Integration',
    'summary': 'Manage Monster Job board integrations with skills',
    'description': """
Module for Monster integration with skills.
===========================================
This module allows to automatically adds the skills from the job offers
to the Monster job posts.
""",
    'depends': [
        'hr_recruitment_skills',
        'hr_recruitment_integration_monster',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
