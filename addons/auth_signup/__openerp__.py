# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

{
    'name': 'Signup',
    'description': """
Allow users to sign up.
=======================
    """,
    'author': 'OpenERP SA',
    'version': '1.0',
    'category': 'Authentication',
    'website': 'http://www.openerp.com',
    'installable': True,
    'depends': ['base_setup'],
    'data': ['res_config.xml'],
    'js': ['static/src/js/auth_signup.js'],
    'qweb': ['static/src/xml/auth_signup.xml'],
}
