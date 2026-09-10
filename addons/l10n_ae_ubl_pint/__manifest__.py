{
    'name': 'UAE - UBL PINT',
    'countries': ['ae'],
    'category': 'Accounting/Localizations/EDI',
    'description': """
    The UBL PINT e-invoicing format for UAE is based on the Peppol International (PINT) model for Billing.
    """,
    'depends': ['account_edi_ubl_cii', 'account_peppol', 'l10n_ae'],
    'data': [
        'wizard/account_move_reversal_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/account_payment_term_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'author': 'Odoo S.A.',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
}
