# -*- coding: utf-8 -*-
{
    'name': "Hr Recruitment Interview Forms",
    'version': '1.0',
    'category': 'Human Resources Survey',
    'summary': 'Surveys',
    'description': """
        Use interview forms during recruitment process.
        This module is integrated with the survey module
        to allow you to define interviews for different jobs.
    """,
    'depends': ['survey', 'hr_recruitment'],
    'data': [
        'security/hr_recruitment_survey_security.xml',
        'security/ir.model.access.csv',
        'data/survey_survey_data.xml',
        'views/hr_job_views.xml',
        'views/hr_applicant_views.xml',
    ],
    'demo': [
        'data/hr_job_demo.xml',
    ],
    'test': ['test/recruitment_process.yml'],
    'auto_install': False,
}
