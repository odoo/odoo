# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sales - Project",
    'summary': "Task Generation from Sales Orders",
    'description': """
Allows to create task from your sales order
=============================================
This module allows to generate a project/task from sales orders.
""",
    'category': 'Hidden',
    'depends': ['sale_management', 'sale_service', 'project_account'],
    'auto_install': ['sale_management', 'project_account'],
    'data': [
        'security/ir.model.access.csv',
        'security/sale_project_security.xml',
        'views/product_views.xml',
        'views/project_task_views.xml',
        'views/sale_order_line_views.xml',
        'views/sale_order_views.xml',
        'views/sale_project_portal_templates.xml',
        'views/project_sharing_views.xml',
        'views/project_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sale_project/static/src/components/project_right_side_panel/**/*',
        ],
        'web.assets_tests': [
            'sale_project/static/tests/tours/**/*',
        ],
    },
    'post_init_hook': '_set_allow_billable_in_project',
    'license': 'LGPL-3',
}
