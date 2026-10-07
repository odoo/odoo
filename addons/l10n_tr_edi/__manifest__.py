{
    'name': 'Türkiye - E-Documents',
    'category': 'Accounting/Localizations/EDI',
    'description': """
Provider-independent base for the Turkish electronic documents regulated by the GİB
(e-Invoice, e-Archive, e-Dispatch).

The documents are exchanged through an integrator, which is implemented in its own module.
    """,
    'depends': ['l10n_tr', 'account_edi_ubl_cii'],
    'data': [
        'security/ir.access.csv',
        'data/account_incoterms_data.xml',
        'data/uom_data.xml',
        'views/l10n_tr_edi_invoice_sequence_views.xml',
        'views/l10n_tr_edi_tax_code_views.xml',
        'views/product_views.xml',
    ],
    'post_init_hook': '_l10n_tr_nilvera_post_init',
    'uninstall_hook': 'uninstall_hook',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
