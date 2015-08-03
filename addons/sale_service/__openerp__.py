# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Create Tasks from SO',
    'version': '1.0',
    'category': 'Project Management',
    'description': """
Automatically creates project tasks from procurement lines.
===========================================================

This module will automatically create a new task for each procurement order line
(e.g. for sale order lines), if the corresponding product meets the following
characteristics:

    * Product Type = Service
    * Create Task Automatically = True

If on top of that a project is specified on the product form (in the Procurement
tab), then the new task will be created in that specific project. Otherwise, the
new task will not belong to any project, and may be added to a project manually
later.

When the project task is completed or cancelled, the corresponding procurement
is updated accordingly. For example, if this procurement corresponds to a sale
order line, the sale order line will be considered delivered when the task is
completed.
""",
    'author': 'Odoo SA',
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['project', 'procurement', 'sale', 'procurement_jit'],
    'data': [
        'views/procrument_views.xml',
        'views/project_task_views.xml',
        'views/product_views.xml'
        ],
    'demo': [
        'data/sale_order_line_demo.xml',
        'data/project_task_type_demo.xml'
        ],
    'installable': True,
}
