# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Stock Analytics',
    'version': '1.0',
    'summary': 'Generate analytic costs for stock pickings linked to your projects',
    'category': 'Services/Project',
    'depends': ['stock_account', 'project_stock'],
    'data': [
        'views/stock_picking_type_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
