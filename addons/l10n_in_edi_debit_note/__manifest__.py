{
    'name': 'Indian E-invoice Debit Note',
    'countries': ['in'],
    'category': 'Accounting/Localizations/Account Charts',
    'summary': "Indian E-invoice Debit Note",
    'description': """
This module allows you to create debit notes in Odoo for Indian accounting.
It extends the functionality of the standard debit note feature to comply with Indian accounting practices.
    """,
    'depends': ['l10n_in_edi', 'account_debit_note'],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
