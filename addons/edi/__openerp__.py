# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2011 OpenERP S.A. <http://openerp.com>
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
    'name': 'Electronic Data Interchange (EDI)',
    'version': '1.0',
    'category': 'Tools',
    'complexity': "easy",
    'description': """
Provides a common EDI platform that other Applications can use
==============================================================

OpenERP specifies a generic EDI format for exchanging business
documents between different systems, and provides generic
mechanisms to import and export them.

More details about OpenERP's EDI format may be found in the
technical OpenERP documentation at http://doc.openerp.com
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'test': [
        'test/edi_partner_test.yml',
    ],
    'js': [
        'static/src/js/sessionless.js',
        'static/src/js/edi_import.js',
        'static/src/js/edi_view.js',
        'static/src/js/edi_invoice.js',
        'static/src/js/edi_sale_purchase_order.js',
    ],
    'installable': True,
    'active': False,
    'certificate': '002046536359186',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: