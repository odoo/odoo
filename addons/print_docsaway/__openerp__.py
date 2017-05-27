# -*- coding: utf-8 -*-
{
    'name': 'Print Provider : DocsAway',
    'summary': 'Print and Send Invoices with DocsAway.com',
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module allows you to send your documents through postal mail, thanks to Docsaway.
======================================================================================
    """,
    'author': 'Odoo SA',
    'depends': ['print'],
    'data': [
        'views/print_docsaway_views.xml',
        'data/print_docsaway_data.xml',
    ],
    'installable': True,
    'auto_install': True,
}
