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
    'name': 'Document Management - Wiki',
    'version': '1.0.1',
    'category': 'Tools',
    'description': """
The base module to manage documents(wiki).
==========================================

Keep track of Wiki groups, pages, and history.
    """,
    'author': ['OpenERP SA', 'Axelor'],
    'website': 'http://openerp.com',
    'depends': ['knowledge'],
    'web_depends': ['widget_wiki'],
    'init_xml': [],
    'update_xml': [
        'wizard/wiki_wiki_page_open_view.xml',
        'wizard/wiki_create_menu_view.xml',
        'wizard/wiki_make_index_view.xml',
        'wizard/wiki_show_diff_view.xml',
        'wiki_view.xml',
        'data/wiki_quickstart.xml',
        'data/wiki_main.xml',
        'security/wiki_security.xml',
        'security/ir.model.access.csv'
    ],
    'demo_xml': ['wiki_demo.xml'],
    'test': ['test/wiki_test00.yml'],
    'installable': True,
    'active': False,
    'certificate': '0086363630317',
    'web': True,
    'images': ['images/create_index.jpeg','images/page_history.jpeg','images/wiki_groups.jpeg','images/wiki_pages.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
