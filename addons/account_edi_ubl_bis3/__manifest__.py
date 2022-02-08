# -*- coding: utf-8 -*-
{
    'name': 'Import/Export invoices with UBL (BIS3)',
    'description': '''
    Support for Export/Import in UBL format (BIS3).
    ''',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['account_edi_ubl'],
    'data': [
        'data/bis3_templates.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
