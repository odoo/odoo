# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012-today OpenERP SA (<http://www.openerp.com>)
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
    'name': 'Reset Password',
    'description': """
Allows the administrator to send a reset password e-mail through the user form. Users will then be able to choose their password following the onscreen instructions.
=====================================================================================================================================================================
""",
    'author': 'OpenERP SA',
    'version': '1.0',
    'category': 'Authentication',
    'website': 'http://www.openerp.com',
    'installable': True,
    'depends': ['auth_signup', 'email_template'],
    'data': [
        'auth_reset_password.xml',
        'res_users_view.xml',
    ],
    'js': ['static/src/js/reset_password.js'],
    'qweb': ['static/src/xml/reset_password.xml'],
}
