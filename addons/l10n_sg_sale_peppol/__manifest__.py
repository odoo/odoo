{
    'name': "Import electronic orders with PEPPOL",
    'category': 'Sales/Sales',
    'description': """
Receive PEPPOL UBL BIS Advanced Orders and automatically generate sale orders
    """,
    'depends': ['l10n_sg', 'sale_edi_ubl'],
    'auto_install': True,
    'post_init_hook': '_l10n_sg_sale_peppol_post_init',
    'uninstall_hook': '_l10n_sg_sale_peppol_uninstall',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'data': [
        'views/sale_order_views.xml',

        'security/ir.access.csv',
    ],
}
