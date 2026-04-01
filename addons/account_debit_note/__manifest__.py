# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Debit Notes',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Debit Notes',
    'description': """
In a lot of countries, a debit note is used as an increase of the amounts of an existing invoice 
or in some specific cases to cancel a credit note. 
It is like a regular invoice, but we need to keep track of the link with the original invoice.  
The wizard used is similar as the one for the credit note.
    """,
    'depends': ['account'],
    'data': [
        'wizard/account_debit_note_view.xml',
        'views/account_move_view.xml',
        'views/account_journal_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
