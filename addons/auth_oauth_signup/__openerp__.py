# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2012 OpenERP SA (<http://openerp.com>).
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
    'name': 'Signup with OAuth2 Authentication',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
Allow users to sign up through OAuth2 Provider.
===============================================
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['auth_oauth', 'auth_signup'],
    'data': [],
    'js': ['static/src/js/auth_oauth_signup.js'],
    'css': [],
    'qweb': [],
    'installable': True,
    'auto_install': True,
}
