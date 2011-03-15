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
    'category': 'Generic Modules/Accounting',
    'description': """
    This module maintains internal sequence number for accounting entries.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'images': ['images/internal_sequence_number.jpeg'],
    'depends': ['account'],
    'init_xml': [],
    'update_xml': [
        'account_sequence_data.xml',
        'account_sequence_installer_view.xml',
        'account_sequence.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '00475376442024623469',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
