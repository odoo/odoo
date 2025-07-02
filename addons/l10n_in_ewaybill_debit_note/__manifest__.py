{
    'name': 'Indian E-waybill Debit Note',
    'countries': ['in'],
    'category': 'Accounting/Localizations/Account Charts',
    'summary': "Indian E-waybill Debit Note",
    'description': """
This module allows you to create debit notes in Odoo for Indian accounting.
It extends the functionality of the standard debit note feature to comply with Indian accounting practices.
    """,
    'depends': ['l10n_in_edi_ewaybill', 'l10n_in_edi_debit_note'],
    'auto_install': True,
    'installable': True,
    'license': 'LGPL-3',
}
