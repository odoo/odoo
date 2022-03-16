# -*- coding: utf-8 -*-
{
    'name': 'Electronic Data Interchange',
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
    'depends': ['base', 'mail', 'uom'],
    'data': [
        'security/edi_security.xml',
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/edi_flow_views.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
