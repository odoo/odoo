# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Leave Management',
    'version': '1.5',
    'category': 'Human Resources',
    'sequence': 27,
    'summary': 'Holidays, Allocation and Leave Requests',
    'website': 'https://www.odoo.com/page/employees',
    'description': """
Manage leave requests and allocations
=====================================

This application controls the leave schedule of your company. It allows employees to request leaves. Then, managers can review requests for leaves and approve or reject them. This way you can control the overall leave planning for the company or department.

You can configure several kinds of leaves (sickness, paid days, ...) and allocate leaves to an employee or department quickly using leave allocation. An employee can also make a request for more days off by making a new Leave allocation. It will increase the total of available days for that leave type (if the request is accepted).

You can keep track of leaves in different ways by following reports:

* Leaves Summary
* Leaves by Department
* Leaves Analysis

A synchronization with an internal agenda (Meetings of the CRM module) is also possible in order to automatically create a meeting when a leave request is accepted by setting up a type of meeting in Leave Type.
""",
    'depends': ['hr', 'calendar', 'resource'],
    'data': [
        'data/report_paperformat.xml',
        'data/hr_holidays_data.xml',

        'security/hr_holidays_security.xml',
        'security/ir.model.access.csv',

        'views/resource_views.xml',
        'views/hr_holidays_views.xml',
        'views/hr_views.xml',

        'wizard/hr_holidays_summary_department_views.xml',
        'wizard/hr_holidays_summary_employees_views.xml',

        'report/hr_holidays_templates.xml',
        'report/hr_holidays_reports.xml',
        'report/hr_holidays_leaves_report_views.xml',
        'report/hr_holidays_views.xml',
    ],
    'demo': [
        'data/hr_holidays_demo.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
