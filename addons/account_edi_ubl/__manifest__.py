# -*- coding: utf-8 -*-
{
    'name': 'Import/Export base for UBL',
    'description': '''
    Base module for ubl managment. Includes common methods and helpers to common to different ubl implementations.
    ''',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['account_edi'],
    'data': [
        'data/ubl_templates.xml',
        'data/en_16931_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
