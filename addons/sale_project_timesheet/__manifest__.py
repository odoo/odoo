# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Timesheet from Project',
    'category': 'Hidden',
    'summary': 'Sell based on project timesheets',
    'description': """
Allows to sell timesheets in your sales order
=============================================

This module set the right product on all timesheet lines
according to the order/contract you work on. This allows to
have real delivered quantities in sales orders.
""",
    'depends': ['sale_timesheet', 'project_timesheet'],
    'data': [
        'security/ir.model.access.csv',
        'security/sale_project_timesheet_security.xml',
        'views/sale_order_views.xml',
        'views/product_views.xml',
        'views/project_overview_views.xml',
        'views/project_views.xml',
        'views/hr_timesheet_templates.xml',
        'report/project_profitability_report_analysis_views.xml',
        'data/sale_project_timesheet_data.xml',
        'wizard/project_task_assign_so_line_views.xml',
        'wizard/project_create_sale_order_views.xml',
        'wizard/project_create_invoice_views.xml',
    ],
    'demo': [
        'data/sale_project_timesheet_demo.xml',
    ],
    'qweb': [
        'static/src/xml/timesheet_plan.xml',
    ],
    'auto_install': True,
}
