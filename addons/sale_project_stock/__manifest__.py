# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Inventory Operations Traceability in Project Updates',
    'version': '1.0',
    'description': """Access full traceability of inventory operations related to the sales order associated with the
    analytic account of your projects in your profitability report.""",
    'summary': """
Access full traceability of inventory operations related to the sales order associated with the analytic account of your
projects in your profitability report.
    """,
    'license': 'LGPL-3',
    'category': 'Services/Project',
    'depends': ['sale_project', 'sale_stock'],
    'data': [
        'views/stock_move_views.xml',
    ],
    'auto_install': True,
}
