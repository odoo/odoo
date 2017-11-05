# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.

{
    'name': 'Belgium - Structured Communication',
    'version': '1.2',
    'author': 'Noviat',
    'website': 'https://www.odoo.com/page/accounting',
    'category': 'Localization',
    'description': """
    
Belgian localization for in- and outgoing invoices (prereq to account_coda):
============================================================================
    - Rename 'reference' field labels to 'Communication'
    - Add support for Belgian Structured Communication

A Structured Communication can be generated automatically on outgoing invoices according to the following algorithms:
---------------------------------------------------------------------------------------------------------------------
    1) Random : +++RRR/RRRR/RRRDD+++
        **R..R =** Random Digits, **DD =** Check Digits
    2) Date : +++DOY/YEAR/SSSDD+++
        **DOY =** Day of the Year, **SSS =** Sequence Number, **DD =** Check Digits
    3) Customer Reference +++RRR/RRRR/SSSDDD+++
        **R..R =** Customer Reference without non-numeric characters, **SSS =** Sequence Number, **DD =** Check Digits  
        
The preferred type of Structured Communication and associated Algorithm can be
specified on the Partner records. A 'random' Structured Communication will
generated if no algorithm is specified on the Partner record. 

    """,
    'depends': ['account'],
    'data' : [
        'data/mail_template_data.xml',
        'views/res_partner_view.xml',
        'views/account_invoice_view.xml',        
        'views/report_invoice.xml',
    ],
}
