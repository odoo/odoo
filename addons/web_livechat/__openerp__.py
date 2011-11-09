# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2011 OpenERP s.a. (<http://openerp.com>).
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
    'name': 'Live Chat Support',
    'version': '2.0',
    'category': 'Hidden',
    'complexity': "easy",
    'description': """
Enable live chat support for those who have a maintenance contract.
===================================================================

Add "Support" button in header from where you can access OpenERP Support.
    """,
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'depends': ['base'],
    'update_xml': [],
    'js' : [
        'static/src/js/web_livechat.js',
    ],
    'css' : [
        'static/src/css/lc.css',
    ],
    'installable': True,
    'active': False,
    'certificate': '0013762192410413',
    'images': ['static/src/img/web_livechat_support.jpeg'],
}
