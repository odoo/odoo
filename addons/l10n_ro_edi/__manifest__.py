{
    'author': 'Odoo',
    'name': 'Romania - E-invoicing',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
E-invoice implementation for Romania
    """,
    'summary': "E-Invoice implementation for Romania",
    'countries': ['ro'],
    'depends': [
        'account_edi_ubl_cii',
        'l10n_ro',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
