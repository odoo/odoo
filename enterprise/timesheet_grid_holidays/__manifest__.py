# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Timesheets And Timeoff",
    'summary': "Link between timesheet and time off",
    'description': """
This module prevents taking time offs into account when computing employee overtime.
    """,

    'category': 'Services/Timesheets',
    'version': '1.0',

    'depends': ['project_timesheet_holidays', 'timesheet_grid'],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend_lazy': [
            'timesheet_grid_holidays/static/src/**/*',
        ],
    }
}
