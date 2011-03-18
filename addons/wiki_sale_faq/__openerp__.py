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
    'name': 'Wiki - Sale-FAQ',
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module provides a Wiki Sales FAQ Template.
===============================================
    """,
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'images': ['images/sale_document.jpeg','images/wiki_pages.jpeg'],
    'depends': ['wiki_faq','document','crm'],
    'init_xml': [
            'wiki_sale_faq_data.xml'
    ],
    'update_xml': [
            'wiki_sale_faq_view.xml'
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
    'certificate' : '00556456617408499693',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
