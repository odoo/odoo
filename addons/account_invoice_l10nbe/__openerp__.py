# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    
#    Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.
# 
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Add support for Belgian structured communication to Invoices',
    'version': '1.2',
    'license': 'AGPL-3',
    'author': 'Noviat',
    'category' : 'Localization/Accounting',
    'description': """
    
Belgian localisation for in- and outgoing invoices (prereq to account_coda):
    - Rename 'reference' field labels to 'Communication'
    - Add support for Belgian Structured Communication

A Structured Communication can be generated automatically on outgoing invoices according to the following algorithms:
    1) Random : +++RRR/RRRR/RRRDD+++
        R..R = Random Digits, DD = Check Digits
    2) Date : +++DOY/YEAR/SSSDD+++
        DOY = Day of the Year, SSS = Sequence Number, DD = Check Digits)
    3) Customer Reference +++RRR/RRRR/SSSDDD+++
        R..R = Customer Reference without non-numeric characters, SSS = Sequence Number, DD = Check Digits)  
        
The preferred type of Structured Communication and associated Algorithm can be specified on the Partner records. 
A 'random' Structured Communication will generated if no algorithm is specified on the Partner record. 

    """,
    'depends': ['account', 'account_cancel'],
    'demo_xml': [],
    'init_xml': [],
    'update_xml' : [
        'partner_view.xml',
        'account_invoice_view.xml',        
    ],
    'active': False,
    'installable': True,}
