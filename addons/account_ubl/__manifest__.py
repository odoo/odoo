# -*- coding: utf-8 -*-
{
    'name': 'UBL',
    'version': '0.1',
    'category': 'Hidden',
    'summary': 'Universal Business Language (UBL)',
    'description': """
This is the base module for the implementation of the `Universal Business Language (UBL)
<http://ubl.xml.org/>`_ standard.  The UBL standard became the `ISO/IEC 19845 
<http://www.iso.org/iso/catalogue_detail.htm?csnumber=66370>`_ standard in January 2016 
(cf the `official announce <http://www.prweb.com/releases/2016/01/prweb13186919.htm>`_).
    """,
    'depends': ['account'],
    'data': [
        'data/templates/ubl_invoice.xml',
        'data/templates/ubl_invoice_e_fff.xml',
    ],
    'installable': True,
    'auto_install': False,
}