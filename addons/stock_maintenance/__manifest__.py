# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Stock - Maintenance',
    'version': '1.0',
    'category': 'Supply Chain/Inventory',
    'description': """
Stock in Maintenance
====================
Open the record of the serial number from an equipment form
""",
    'depends': ['stock', 'maintenance'],
    'data': [
        'views/maintenance_views.xml',
        'views/stock_location.xml',
    ],
    'summary': 'See lots used in maintenance',
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
