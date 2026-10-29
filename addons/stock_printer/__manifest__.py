# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Inventory - Network Printers",
    'version': '1.0',
    'category': 'Supply Chain/Inventory',
    'summary': "Print shipping labels and other reports on the printers of the warehouse",
    'description': """
Manage the printers of the local network from Inventory, and print the carrier
labels and export documents of the transfers on them, automatically when the
transfers are validated.
""",
    'depends': ['printer', 'stock'],
    'data': [
        'security/ir.access.csv',
        'report/stock_printer_reports.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_printer_menus.xml',
    ],
    'demo': [
        'data/printer_demo.xml',
    ],
    'auto_install': ['stock'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
