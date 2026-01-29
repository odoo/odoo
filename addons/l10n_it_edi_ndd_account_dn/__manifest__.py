{
    'name': 'Italy - E-invoicing - Bridge module between Italy NDD and Account Debit Note',
    'countries': ['it'],
    'version': '1.0',
    'depends': [
        'l10n_it_edi_ndd',
        'account_debit_note',
    ],
    'auto_install': ['l10n_it_edi_ndd'],
    'description': """
Bridge module to support the debit notes (nota di debito - NDD) by adding debit note fields.
    """,
    'category': 'Accounting/Localizations/EDI',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/italy.html',
    'data': [
        'data/invoice_it_template.xml',
    ],
    'license': 'LGPL-3',
}
