# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sales Timesheet: Invoicing",

    'summary': "Configure timesheet invoicing",

    'description': """
When invoicing timesheets, allows invoicing either all timesheets
linked to an SO, or only the validated timesheets
    """,

    'category': 'Hidden',
    'version': '0.1',

    'depends': ['sale_timesheet', 'timesheet_grid'],
    'data': [
        'data/sale_timesheet_enterprise_data.xml',
        'security/ir.model.access.csv',
        'views/account_invoice_views.xml',
        'views/hr_timesheet_tip_views.xml',
        'views/hr_timesheet_views.xml',
        'views/hr_employee_views.xml',
        'views/project_task_views.xml',
        'views/project_sharing_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_timesheet_enterprise_menus.xml',
        'views/project_portal_template.xml',
        'wizard/sale_make_invoice_advance_views.xml',
        'report/timesheets_analysis_views.xml',
    ],
    'demo': [
        'data/sale_timesheet_enterprise_demo.xml'
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'sale_timesheet_enterprise/static/src/**/*',
            ('remove', 'sale_timesheet_enterprise/static/src/views/pivot/**'),
            ('remove', 'sale_timesheet_enterprise/static/src/views/timer_timesheet_grid/**'),
            ('remove', 'sale_timesheet_enterprise/static/src/views/timesheet_grid/**'),
            ('remove', 'sale_timesheet_enterprise/static/src/views/timesheet_leaderboard_timer_grid/**'),
        ],
        'web.assets_backend_lazy': [
            'sale_timesheet_enterprise/static/src/views/pivot/**',
            'sale_timesheet_enterprise/static/src/views/timer_timesheet_grid/**',
            'sale_timesheet_enterprise/static/src/views/timesheet_grid/**',
            'sale_timesheet_enterprise/static/src/views/timesheet_leaderboard_timer_grid/**',
        ],
        'web.qunit_suite_tests': [
            'sale_timesheet_enterprise/static/tests/**/*.js',
        ],
    }
}
