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
        'data/account_edi_data.xml',
        'data/ubl_20_templates_common.xml',
        'data/ubl_20_templates_invoice.xml',
        'data/ubl_21_templates_invoice.xml',
        'data/ubl_bis3_templates_common.xml',
        'data/ubl_bis3_templates_invoice.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
