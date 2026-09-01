# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Inventory Analytics',
    'summary': 'Generate analytic costs for inventory transfers linked to your projects',
    'category': 'Services/Project',
    'depends': ['stock_account', 'project_stock'],
    'data': [
        'views/stock_picking_type_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
