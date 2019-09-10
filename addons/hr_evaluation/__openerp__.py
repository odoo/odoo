# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
    'name': 'Employee Appraisals',
    'version': '0.1',
    'author': 'OpenERP SA',
    'category': 'Human Resources',
    'sequence': 31,
    'website': 'https://www.odoo.com/page/appraisal',
    'summary': 'Periodical Evaluations, Appraisals, Surveys',
    'depends': ['hr', 'calendar', 'survey'],
    'description': """
Periodical Employees evaluation and appraisals
==============================================

By using this application you can maintain the motivational process by doing periodical evaluations of your employees' performance. The regular assessment of human resources can benefit your people as well your organization.

An evaluation plan can be assigned to each employee. These plans define the frequency and the way you manage your periodic personal evaluations. You will be able to define steps and attach interview forms to each step.

Manages several types of evaluations: bottom-up, top-down, self-evaluations and the final evaluation by the manager.

Key Features
------------
* Ability to create employees evaluations.
* An evaluation can be created by an employee for subordinates, juniors as well as his manager.
* The evaluation is done according to a plan in which various surveys can be created. Each survey can be answered by a particular level in the employees hierarchy. The final review and evaluation is done by the manager.
* Every evaluation filled by employees can be viewed in a PDF form.
* Interview Requests are generated automatically by OpenERP according to employees evaluation plans. Each user receives automatic emails and requests to perform a periodical evaluation of their colleagues.
""",
    "data": [
        'security/ir.model.access.csv',
        'security/hr_evaluation_security.xml',
        'hr_evaluation_view.xml',
        'report/hr_evaluation_report_view.xml',
        'survey_data_appraisal.xml',
        'hr_evaluation_data.xml',
        'hr_evaluation_installer.xml',
    ],
    "demo": ["hr_evaluation_demo.xml"],
    # 'test': [
    #     'test/test_hr_evaluation.yml',
    #     'test/hr_evalution_demo.yml',
    # ],
    'auto_install': False,
    'installable': True,
    'application': True,
}
