# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# TODO: [XBO] merge with sale_timesheet module in master
{
    'name': 'Sales Timesheet Edit',
    'category': 'Hidden',
    'summary': 'Edit the sale order line linked in the timesheets',
    'description': """
Allow to edit sale order line in the timesheets
===============================================

This module adds the edition of the sale order line
set in the timesheets. This allows adds more flexibility
to the user to easily change the sale order line on a
timesheet in task form view when it is needed.
""",
    'depends': ['sale_timesheet'],
    'data': [
        'views/assets.xml',
        'views/project_task.xml',
    ],
    'demo': [],
    'auto_install': True,
}
