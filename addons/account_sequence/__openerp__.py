# -*- coding: utf-8 -*-

{
    'name': 'Entries Sequence Numbering',
    'version': '1.1',
    'category': 'Accounting & Finance',
    'description': """
This module maintains internal sequence number for accounting entries.
======================================================================

Allows you to configure the accounting sequences to be maintained.

You can customize the following attributes of the sequence:
-----------------------------------------------------------
    * Prefix
    * Suffix
    * Next Number
    * Increment Number
    * Number Padding
    """,
    'author': 'Odoo',
    'website': 'https://www.odoo.com',
    'depends': ['account'],
    'data': [
        'account_sequence_data.xml',
        'account_sequence_installer_view.xml',
        'account_sequence.xml'
    ],
    'demo': [],
    'installable': True,
}
