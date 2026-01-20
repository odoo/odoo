{
    'name': "Import/Export electronic purchase orders with Peppol",
    'category': 'Supply Chain/Purchase',
    'description': """
Allows BIS advanced ordering for purchase module.
    """,
    'depends': ['l10n_sg', 'purchase_edi_ubl_bis3'],
    'data': [
        'views/purchase_view.xml',
        'security/ir.access.csv',
    ],
    'auto_install': True,
    'post_init_hook': '_l10n_sg_purchase_peppol_post_init',
    'uninstall_hook': '_l10n_sg_purchase_peppol_uninstall',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
