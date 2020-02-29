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
    'depends': ['sale_management', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'security/sale_project_security.xml',
        'views/product_views.xml',
        'views/project_task_views.xml',
        'views/sale_order_views.xml',
    ],
    'auto_install': True,
}
