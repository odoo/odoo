{
    'name': 'Spain - Facturae EDI - Invoice Period',
    'version': '1.0',
    'description': """
    Patch module to add the missing Invoice Period in the Facturae EDI.
    """,
    'license': 'LGPL-3',
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'l10n_es_edi_facturae',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'auto_install': True,
}
