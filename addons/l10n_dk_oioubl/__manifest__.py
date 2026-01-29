{
    'author': 'Odoo',
    'name': 'Denmark - E-invoicing',
    'version': '0.1',
    'category': 'Accounting/Localizations/EDI',
    'description': """
E-invoice implementation for the Denmark
    """,
    'summary': "E-Invoicing, Offentlig Information Online Universal Business Language",
    'countries': ['dk'],
    'depends': [
        'account_edi_ubl_cii',
        'l10n_dk',
    ],
    'data': [
        'data/oioubl_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
