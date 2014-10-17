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
    'website': 'https://www.odoo.com/page/blog-engine',
    'summary': 'News, Blogs, Announces, Discussions',
    'version': '1.0',
    'description': """
OpenERP Blog
============

        """,
    'author': 'OpenERP SA',
    'depends': ['knowledge', 'website_mail', 'website_partner'],
    'data': [
        'data/website_blog_data.xml',
        'views/website_blog_views.xml',
        'views/website_blog_templates.xml',
        'security/ir.model.access.csv',
        'security/website_blog.xml',
    ],
    'demo': [
        'data/website_blog_demo.xml'
    ],
    'test': [
        'tests/test_website_blog.yml'
    ],
    'qweb': [
        'static/src/xml/*.xml'
    ],
    'installable': True,
    'application': True,
}
