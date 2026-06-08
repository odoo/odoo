{
    'name': 'France - UBL/CII formats',
    'category': 'Accounting/Localizations/EDI',
    'website': "https://www.odoo.com/documentation/18.0/applications/finance/fiscal_localizations/france.html",
    'description': """
        - Adds mandatory fields in Factur-x for France invoices
        - Adds UBL 21 for France invoices
""",
    'depends': [
        'l10n_fr_account',
        'account_edi_ubl_cii_tax_extension',
    ],
    'data': [],
    'license': 'LGPL-3',
    'post_init_hook': '_post_init',
    'uninstall_hook': 'uninstall_hook',
}
