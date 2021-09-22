# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Timesheet',
    'category': 'Hidden',
    'summary': 'Sell based on timesheets',
    'description': """
Allows to sell timesheets in your sales order
=============================================

This module set the right product on all timesheet lines
according to the order/contract you work on. This allows to
have real delivered quantities in sales orders.
""",
    'depends': ['sale_project', 'hr_timesheet'],
    'data': [
        'data/sale_service_data.xml',
        'security/ir.model.access.csv',
        'security/sale_timesheet_security.xml',
        'views/account_invoice_views.xml',
        'views/sale_order_views.xml',
        'views/product_views.xml',
        'views/project_task_views.xml',
        'views/project_update_templates.xml',
        'views/hr_timesheet_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_timesheet_portal_templates.xml',
        'views/project_sharing_views.xml',
        'report/project_profitability_report_analysis_views.xml',
        'data/sale_timesheet_filters.xml',
        'wizard/project_create_sale_order_views.xml',
        'wizard/project_create_invoice_views.xml',
        'wizard/sale_make_invoice_advance_views.xml',
    ],
    'demo': [
        'data/sale_service_demo.xml',
    ],
    'auto_install': True,
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'sale_timesheet/static/src/scss/sale_timesheet_portal.scss',
        ],
        'web.assets_backend': [
            'sale_timesheet/static/src/js/so_line_one2many.js',
        ],
        'web.assets_tests': [
            'sale_timesheet/static/tests/**/*',
        ],
        'web.assets_qweb': [
            'sale_timesheet/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
