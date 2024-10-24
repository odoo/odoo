# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Stock Analytics',
    'version': '1.0',
    'summary': 'Track the costs of stock pickings associated with the analytic accounts of your projects.',
    'category': 'Services/Project',
    'depends': ['stock_account', 'project_stock'],
    'data': [
        'views/stock_picking_type_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
