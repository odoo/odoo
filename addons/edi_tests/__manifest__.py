# -*- coding: utf-8 -*-
{
    'name': 'Electronic Data Interchange Tests',
    'description': """
Electronic Data Interchange
=======================================
EDI is the electronic interchange of business information using a standardized format.

This is the base module for import and export of documents in various EDI formats, and the
the transmission of said documents to various parties involved in the exchange (other company,
governements, etc.)
    """,
    'author': "Odoo",
    'version': '1.0',
    'category': 'Productivity/Edi',
    'depends': ['edi'],
    'data': [
        'data/account_edi_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
