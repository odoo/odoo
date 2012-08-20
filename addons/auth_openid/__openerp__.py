# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
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
    'name': 'OpenID Authentification',
    'version': '2.0',
    'category': 'Tools',
    'description': """
Allow users to login through OpenID.
====================================
""",
    'author': 'OpenERP s.a.',
    'maintainer': 'OpenERP s.a.',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'web'],
    'data': [
        'res_users.xml',
    ],
    'js': [
        'static/src/js/auth_openid.js',
    ],
    'css': [
        'static/src/css/openid.css',
    ],
    'qweb': [
        'static/src/xml/auth_openid.xml',
    ],
    'external_dependencies': {
        'python' : ['openid'],
    },
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
