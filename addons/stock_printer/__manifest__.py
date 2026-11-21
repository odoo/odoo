{
    'name': "Stock - Printer",
    'summary': "Manage Zebra/EPSON printers from Inventory",
    'category': 'Supply Chain/Inventory',
    'depends': ['stock', 'printer'],
    'data': [
        'views/stock_menu_views.xml',
        'security/ir.access.csv',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
