# -*- encoding: utf-8 -*-
{
    'name': 'Account Bank Statement Import',
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['account_accountant', 'base_import'],
    'description': """Generic Wizard to Import Bank Statements.

(This module does not include any type of import format.)

OFX and QIF imports are available in Enterprise version.""",
    'data': [
        'views/account_bank_statement_import_view.xml',
    ],
    'demo': [
        'demo/partner_bank.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'account_bank_statement_import/static/src/**/*',
        ],
    },
    'license': 'OEEL-1',
}
