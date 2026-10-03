{
    'name': 'United Arab Emirates - UBL PINT on Peppol',
    'countries': ['ae'],
    'category': 'Accounting/Localizations/EDI',
    'description': """
    Bridge module between the UAE UBL PINT and Peppol modules.
    It registers the PINT AE document types on the Peppol network.
    """,
    'depends': ['account_peppol', 'l10n_ae_ubl_pint'],
    'demo': [
        'demo/demo_data.xml',
    ],
    'author': 'Odoo S.A.',
    'pre_init_hook': '_pre_init_check_conflict',
    'license': 'LGPL-3',
}
