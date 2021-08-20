# -*- coding: utf-8 -*-
{
    'name' : 'EDI',
    'description':"""
Electronic Data Interchange
=======================================
EDI is the electronic interchange of business information using a standardized format.

This is the base module for import and export in various EDI formats for various models, and the
the transmission of said documents to various parties involved in the exchange (other company,
governements, etc.)
    """,
    'version' : '1.0',
    'category': 'Accounting/Accounting',  # TODO
    'depends' : [],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
