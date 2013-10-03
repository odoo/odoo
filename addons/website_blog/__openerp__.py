# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
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
    'name': 'Blogs',
    'category': 'Website',
    'summary': 'News, Blogs, Announces, Discussions',
    'version': '1.0',
    'description': """
OpenERP Blog
============

        """,
    'author': 'OpenERP SA',
    'depends': ['knowledge', 'website_mail'],
    'data': [
        'website_blog_data.xml',
        'views/website_blog_classic.xml',
        'views/website_blog_templates.xml',
        # 'wizard/document_page_create_menu_view.xml',
        'wizard/document_page_show_diff_view.xml',
        'security/ir.model.access.csv',
        'security/website_mail.xml',
    ],
    'demo': [
        'website_blog_demo.xml'
    ],
    'test': [
        'test/document_page_test00.yml'
    ],
    'qweb': [
        'static/src/xml/*.xml'
    ],
    'installable': True,
}
