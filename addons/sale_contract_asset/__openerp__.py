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
    'name': 'Deferred revenue management for contracts',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
This module allows you to set a deferred revenue on your subscription contracts.
""",
    'author': 'Odoo S.A.',
    'website': 'https://www.odoo.com/',
    'depends': ['sale_contract', 'account_asset'],
    'data': [
        'views/account_analytic_account_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}