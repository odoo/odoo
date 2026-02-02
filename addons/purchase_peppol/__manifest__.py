{
    'name': "Import/Export electronic purchase orders with Peppol",
    'version': '1.0',
    'category': 'Supply Chain/Purchase',
    'description': """
Allows BIS advanced ordering for purchase module.
    """,
    'depends': ['account_peppol', 'purchase_edi_ubl_bis3'],
    'data': [
        'views/purchase_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
