# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Appraisals',
    'version': '1.0',
    'author': 'Odoo S.A',
    'category': 'Human Resources',
    'sequence': 31,
    'website': 'https://www.odoo.com',
    'summary': 'Periodical Appraisal',
    'depends': ['hr', 'calendar', 'survey'],
    'description': """
Periodical Employees appraisal
==============================================

By using this application you can maintain the motivational process by doing periodical appraisals of your employees performance. The regular assessment of human resources can benefit your people as well your organization.

An appraisal plan can be assigned to each employee. These plans define the frequency and the way you manage your periodic personal appraisal.

Key Features
------------
* Ability to create employee's appraisal(s).
* An appraisal can be created by an employee's manager or automatically based on schedule which is defined in the employee form.
* The appraisal is done according to a plan in which various surveys can be created. Each survey can be answered by a particular level in the employees hierarchy. The final review and appraisal is done by the manager.
* Manager, colleague, collaborator, and employee himself/herself receives email to perform a periodical appraisal.
* Every Appraisal Form filled by employees, colleague, collaborator, can be viewed in a PDF form.
* Meeting Requests are created manually according to employees appraisals.
""",
    "data": [
        'security/ir.model.access.csv',
        'security/hr_appraisal_security.xml',
        'views/hr_appraisal_views.xml',
        'report/hr_appraisal_report_views.xml',
        'views/hr_department_views.xml',
        'views/hr_appraisal.xml',
        'data/hr_appraisal_data.xml',
    ],
    "demo": [
        "data/survey_demo_data.xml",
        "data/hr_appraisal_demo.xml",
    ],
    'installable': True,
    'application': True,
}
