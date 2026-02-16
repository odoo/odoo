{
    'name': "Import/Export electronic purchase orders with Peppol",
    'version': '1.0',
    'category': 'Supply Chain/Purchase',
    'description': """
Allows BIS advanced ordering for purchase module.
    """,
    'depends': ['purchase', 'purchase_edi_ubl_bis3'],
    'data': [
        'views/purchase_view.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
