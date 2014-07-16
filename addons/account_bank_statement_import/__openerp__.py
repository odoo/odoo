# -*- encoding: utf-8 -*-
{
    'name': 'Account Bank Statement Import',
    'version': '1.0',
    'author': 'OpenERP SA',
    'depends': ['account'],
    'demo': [],
    'description' : """Generic Wizard to Import Bank Statements""",
    'data' : [
        'views/account_bank_statement_import_view.xml',
    ],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
