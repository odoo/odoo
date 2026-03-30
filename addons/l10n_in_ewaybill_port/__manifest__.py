{
    'name': """Indian - Shipping Ports for E-waybill""",
    'icon': '/l10n_in/static/description/icon.png',
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_in_edi_ewaybill',
    ],
    'description': """
Indian - E-waybill Shipping Ports
====================================
Introduced a new module to manage Indian port codes, specifically for transport
modes classified as Air or Sea in the e-Way Bill system.
    """,
    'data': [
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
}
