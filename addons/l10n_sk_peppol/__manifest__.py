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
        'data/cron.xml',
        'wizard/peppol_registration.xml',
        'views/res_partner_views.xml',
    ],
    'post_init_hook': '_l10n_sk_peppol_post_init_hook',
    'license': 'LGPL-3',
}
