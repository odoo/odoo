# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Document Management - Wiki - Quality Manual',
    'version': '1.0',
    'category': 'Knowledge Management',
    'complexity': "easy",
    'description': """
Quality Manual Template.
========================

It provides demo data, thereby creating a Wiki Group and a Wiki Page
for Wiki Quality Manual.
    """,
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'depends': ['wiki'],
    'init_xml': [],
    'update_xml': ['wiki_quality_manual.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate' : '00705749856097740509',
    'images': ['images/wiki_pages_quality_manual.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
