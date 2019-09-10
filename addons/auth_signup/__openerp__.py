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
Allow users to sign up and reset their password
===============================================
    """,
    'author': 'OpenERP SA',
    'version': '1.0',
    'category': 'Authentication',
    'website': 'https://www.odoo.com',
    'installable': True,
    'auto_install': True,
    'depends': [
        'base_setup',
        'email_template',
        'web',
    ],
    'data': [
        'auth_signup_data.xml',
        'res_config.xml',
        'res_users_view.xml',
        'views/auth_signup_login.xml',
    ],
    'bootstrap': True,
}
