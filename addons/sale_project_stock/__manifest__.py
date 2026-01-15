# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sale Project - Sale Stock',
    'version': '1.0',
    'description': 'Adds a full traceability of inventory operations on the profitability report.',
    'summary': 'Adds a full traceability of inventory operations on the profitability report.',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'category': 'Sales',
    'depends': ['sale_project', 'sale_stock', 'project_stock_account'],
    'data': [
        'views/stock_move_views.xml',
    ],
    'auto_install': True,
}
