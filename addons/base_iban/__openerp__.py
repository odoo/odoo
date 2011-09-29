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
    'name': 'Create IBAN bank accounts',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'complexity': "easy",
    'description': """
This module installs the base for IBAN (International Bank Account Number) bank accounts and checks for its validity.
=====================================================================================================================

The ability to extract the correctly represented local accounts from IBAN accounts with a single statement.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'init_xml': ['base_iban_data.xml'],
    'update_xml': ['base_iban_view.xml'],
    'installable': True,
    'active': False,
    'certificate': '0050014379549',
    'images': ['images/base_iban1.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
