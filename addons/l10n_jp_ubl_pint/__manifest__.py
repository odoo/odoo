{
    'name': 'Japan - UBL PINT',
    'countries': ['jp'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
    The UBL PINT e-invoicing format for Japan is based on the Peppol International (PINT) model for Billing.
    """,
    'depends': ['account_edi_ubl_cii'],
    'installable': True,
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3'
}
