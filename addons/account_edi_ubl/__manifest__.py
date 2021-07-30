# -*- coding: utf-8 -*-
{
    'name': 'Import/Export invoices with generic UBL',
    'description': '''
    Support for Export/Import in UBL format (2.1).
    ''',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['account_edi'],
    'data': [
        'data/ubl_templates.xml',
        'data/account_edi_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
