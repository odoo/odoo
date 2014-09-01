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
    'description': """
Provides a common EDI platform that other Applications can use.
===============================================================

OpenERP specifies a generic EDI format for exchanging business documents between 
different systems, and provides generic mechanisms to import and export them.

More details about OpenERP's EDI format may be found in the technical OpenERP 
documentation at http://doc.openerp.com.
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/api',
    'depends': ['base', 'email_template'],
    'data' : [
        'views/edi.xml',
    ],
    'icon': '/edi/static/src/img/knowledge.png',
    'test': ['test/edi_partner_test.yml'],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
