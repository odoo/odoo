# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 Numérigraphe SARL.
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
    'name': 'French RIB Bank Details',
    'version': '1.0',
    'category': 'Hidden/Dependency',
    'description': """
This module lets users enter the banking details of Partners in the RIB format (French standard for bank accounts details).
===========================================================================================================================

RIB Bank Accounts can be entered in the "Accounting" tab of the Partner form by specifying the account type "RIB". 

The four standard RIB fields will then become mandatory:
--------------------------------------------------------    
    - Bank Code
    - Office Code
    - Account number
    - RIB key
    
As a safety measure, OpenERP will check the RIB key whenever a RIB is saved, and
will refuse to record the data if the key is incorrect. Please bear in mind that
this can only happen when the user presses the 'save' button, for example on the
Partner Form. Since each bank account may relate to a Bank, users may enter the
RIB Bank Code in the Bank form - it will the pre-fill the Bank Code on the RIB
when they select the Bank. To make this easier, this module will also let users
find Banks using their RIB code.

The module base_iban can be a useful addition to this module, because French banks
are now progressively adopting the international IBAN format instead of the RIB format.
The RIB and IBAN codes for a single account can be entered by recording two Bank
Accounts in OpenERP: the first with the type 'RIB', the second with the type 'IBAN'. 
""",
    'author' : u'Numérigraphe SARL',
    'depends': ['account', 'base_iban'],
    'data': ['bank_data.xml', 'bank_view.xml'],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
