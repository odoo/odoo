# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Timesheets',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 80,
    'summary': 'Timesheets, Attendances, Activities',
    'description': """
Record and validate timesheets and attendances easily
=====================================================

This application supplies a new screen enabling you to manage both attendances (Sign in/Sign out) and your work encoding (timesheet) by period. Timesheet entries are made by employees each day. At the end of the defined period, employees validate their sheet and the manager must then approve his team's entries. Periods are defined in the company forms and you can set them to run monthly or weekly.

The complete timesheet validation process is:
---------------------------------------------
* Draft sheet
* Confirmation at the end of the period by the employee
* Validation by the project manager

The validation can be configured in the company:
------------------------------------------------
* Period size (Day, Week, Month)
* Maximal difference between timesheet and attendances
    """,
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['hr_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_timesheet_sheet_security.xml',
        'hr_timesheet_sheet_view.xml',
        'hr_timesheet_workflow.xml',
        'report/hr_timesheet_report_view.xml',
        'wizard/hr_timesheet_current_view.xml',
        'hr_timesheet_sheet_data.xml',
        'res_config_view.xml',
        'views/hr_timesheet_sheet.xml',
        'hr_dashboard.xml',
    ],
    'test':['../account/test/account_minimal_test.xml', 'test/test_hr_timesheet_sheet.yml'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'qweb': ['static/src/xml/timesheet.xml',],
}
