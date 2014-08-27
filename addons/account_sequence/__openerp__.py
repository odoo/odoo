# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com',
    'images': ['images/internal_sequence_number.jpeg'],
    'depends': ['account'],
    'data': [
        'account_sequence_data.xml',
        'account_sequence_installer_view.xml',
        'account_sequence.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
