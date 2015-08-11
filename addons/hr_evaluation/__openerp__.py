# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Appraisals',
    'version': '0.1',
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
        'hr_dashboard.xml',
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
