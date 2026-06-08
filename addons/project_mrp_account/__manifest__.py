# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "MRP Account Project",
    'summary': "Monitor MRP account using project",
    'category': 'Services/Project',
    'depends': ['mrp_account', 'project_mrp', 'project_stock_account'],
    'data': [
        'data/project_mrp_account_data.xml',
        'views/stock_picking_type_views.xml',
    ],
    'demo': [
        'data/project_mrp_account_demo.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
