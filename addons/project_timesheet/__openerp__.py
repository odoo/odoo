# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Bill Time on Tasks',
    'version': '1.0',
    'category': 'Project Management',
    'description': """
Synchronization of project task work entries with timesheet entries.
====================================================================

This module lets you transfer the entries under tasks defined for Project
Management to the Timesheet line entries for particular date and particular user
with the effect of creating, editing and deleting either ways.
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/project-management',
    'images': ['images/invoice_task_work.jpeg', 'images/my_timesheet.jpeg', 'images/working_hour.jpeg'],
    'depends': ['resource', 'project', 'account_analytic_analysis', 'procurement'],
    'data': [
        'security/ir.model.access.csv',
        'security/project_timesheet_security.xml',
        'report/project_report_view.xml',
        'project_timesheet_view.xml',
        'project_dashboard.xml',
    ],
    'demo': ['project_timesheet_demo.xml'],
    'test': [
        'test/worktask_entry_to_timesheetline_entry.yml',
    ],
    'installable': True,
    'auto_install': True,
}
