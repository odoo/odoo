# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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
    ],
    'data': [
        'wizard/hr_recruitment_create_partner_job_view.xml',
        'hr_recruitment_view.xml',
        'hr_recruitment_menu.xml',
        'security/hr_recruitment_security.xml',
        'security/ir.model.access.csv',
        'report/hr_recruitment_report_view.xml',
        'hr_recruitment_installer_view.xml',
        'res_config_view.xml',
        'survey_data_recruitment.xml',
        'hr_recruitment_data.xml',
        'views/hr_recruitment.xml',
    ],
    'demo': ['hr_recruitment_demo.xml'],
    'test': ['test/recruitment_process.yml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
