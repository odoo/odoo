{
    'name': 'United Arab Emirates - UBL PINT',
    'countries': ['ae'],
    'category': 'Accounting/Localizations/EDI',
    'description': """
    The UBL PINT e-invoicing format for UAE is based on the Peppol International (PINT) model for Billing.
    It also registers the PINT AE document types on the Peppol network.
    """,
    'depends': ['account_edi_ubl_cii', 'account_peppol', 'l10n_ae'],
    'data': [
        'wizard/account_move_reversal_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_term_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'author': 'Odoo S.A.',
    'post_init_hook': '_l10n_ae_ubl_pint_post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
