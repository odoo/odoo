# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project Stock',
    'version': '1.0',
    'summary': 'Link Stock pickings to Project',
    'category': 'Services/Project',
    'depends': ['stock', 'project'],
    'data': [
        'views/stock_picking_views.xml',
        'views/project_project_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
