# -*- coding: utf-8 -*-
{
    'name' : 'EDI for Delivery Orders',
    'description':"""
Electronic Data Interchange
===========================
EDI is the electronic interchange of business information using a standardized format.

This is the base module for the export of delivery orders in various EDI formats, and the
the transmission of said documents to various parties involved in the exchange (other company,
governments, etc.)
    """,
    'version' : '1.0',
    'category': 'Accounting/Accounting', #TODO: it is more of a mix
    'depends' : ['account_edi_extended', 'stock'],
    'data': [
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
