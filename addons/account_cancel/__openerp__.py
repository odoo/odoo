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
    'name' : 'Cancel Journal Entries',
    'version' : '1.1',
    'author' : 'OpenERP SA',
    'category': 'Accounting & Finance',
    'description': """
Allows cancelling accounting entries.
=====================================

This module adds 'Allow Cancelling Entries' field on form view of account journal.
If set to true it allows user to cancel entries & invoices.
    """,
    'website': 'http://www.openerp.com',
    'images' : ['images/account_cancel.jpeg'],
    'depends' : ['account'],
    'data': ['account_cancel_view.xml' ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'certificate' : '001101250473177981989',


}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
