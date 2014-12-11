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
    'name': 'Web Shortcuts',
    'version': '1.0',
    'category': 'Tools',
    'description': """
Enable shortcuts feature in the web client.
===========================================

Add a Shortcut icon in the systray in order to access the user's shortcuts (if any).

Add a Shortcut icon besides the views title in order to add/remove a shortcut.
    """,
    'author': 'OpenERP SA',
    'website': 'http://openerp.com',
    'depends': ['base'],
    'data': [],
    'js' : ['static/src/js/web_shortcuts.js'],
    'css' : ['static/src/css/web_shortcuts.css'],
    'qweb' : ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False,
}
