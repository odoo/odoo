{
    'name': 'Slovak - E-Invoicing (Peppol)',
    'icon': '/account/static/description/l10n.png',
    'countries': ['sk'],
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
Peppol is mandatory for Slovak businesses from January 1, 2027.
This module extends the generic Peppol integration with Slovakia-specific features, primarily the generation and
processing of Tax Data Documents (TDD).
It also allows to register a company in the Peppol Directory via the Slovak KYC system.
    """,
    'depends': [
        'l10n_sk',
        'account_peppol',
    ],
    'auto_install': True,
    'data': [
        'wizard/peppol_registration.xml',
    ],
    'license': 'LGPL-3',
}
