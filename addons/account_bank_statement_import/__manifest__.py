# -*- encoding: utf-8 -*-
{
    'name': 'Account Bank Statement Import',
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': ['account'],
    'description': """Generic Wizard to Import Bank Statements.

(This module does not include any type of import format.)

OFX and QIF imports are available in Enterprise version.""",
    'data': [
        'account_bank_statement_import_view.xml',
        'account_import_tip_data.xml',
        'wizard/journal_creation.xml',
        'views/account_bank_statement_import_templates.xml',
    ],
    'demo': [
        'demo/partner_bank.xml',
    ],
    'installable': True,
    'auto_install': True,
}
