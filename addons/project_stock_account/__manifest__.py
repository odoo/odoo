# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Stock Account',
    'version': '1.0',
    'summary': 'Handle analytics in Stock pickings with Project',
    'category': 'Services/Project',
    'depends': ['stock_account', 'project_stock'],
    'data': [
        'views/stock_picking_type_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
