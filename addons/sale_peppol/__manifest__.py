{
    'name': "Import electronic orders with PEPPOL",
    'version': '1.0',
    'category': 'Sales/Sales',
    'description': """
Receive PEPPOL UBL BIS Advanced Orders and automatically generate sale orders
    """,
    'depends': ['sale_edi_ubl', 'account_peppol'],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'data': [
        'views/sale_order_views.xml',
    ],
}
