# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment Process',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 25,
    'summary': 'Jobs, Recruitment, Applications, Job Interviews, Surveys',
    'description': """
Manage job positions and the recruitment process
================================================

This application allows you to easily keep track of jobs, vacancies, applications, interviews...

It is integrated with the mail gateway to automatically fetch email sent to <jobs@yourcompany.com> in the list of applications. It's also integrated with the document management system to store and search in the CV base and find the candidate that you are looking for. Similarly, it is integrated with the survey module to allow you to define interviews for different jobs.
You can define the different phases of interviews and easily rate the applicant from the kanban view.
""",
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/recruitment',
    'depends': [
        'decimal_precision',
        'hr',
        'survey',
        'calendar',
        'fetchmail',
        'web_kanban_gauge',
        'utm',
    ],
    'data': [
        'wizard/hr_recruitment_create_partner_job_view.xml',
        'hr_recruitment_view.xml',
        'security/hr_recruitment_security.xml',
        'security/ir.model.access.csv',
        'report/hr_recruitment_report_view.xml',
        'hr_recruitment_installer_view.xml',
        'res_config_view.xml',
        'survey_data_recruitment.xml',
        'hr_recruitment_data.xml',
        'views/hr_recruitment.xml',
        'hr_dashboard.xml',
        'hr_recruitment_dashboard.xml',
    ],
    'demo': ['hr_recruitment_demo.xml'],
    'test': ['test/recruitment_process.yml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
