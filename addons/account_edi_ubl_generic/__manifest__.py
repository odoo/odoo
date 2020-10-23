# -*- coding: utf-8 -*-
{
    'name': 'Import/Export invoices with generic UBL',
    'description': '''
    Support for Export/Import in UBL format (2.1) and BIS3 (EN16931) format.
    ''',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['account_edi_ubl'],
    'data': [
        'data/account_edi_data.xml',
    ],
    'installable': True,
    'application': False,
}
