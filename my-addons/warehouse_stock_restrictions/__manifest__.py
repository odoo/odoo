# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright © 2016 Techspawn Solutions. (<http://techspawn.in>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': "Warehouse Restrictions",

    'summary': """
         Warehouse and Stock Location Restriction on Users.""",

    'description': """
        This Module Restricts the User from Accessing Warehouse and Process Stock Moves other than allowed to Warehouses and Stock Locations.
    """,

    'author': "Techspawn Solutions",
    'website': "http://www.techspawn.com",

    'category': 'Warehouse',
    'version': '0.2',

    'depends': ['base', 'stock'],

    'data': [
        'users_view.xml',
        'security/security.xml',
    ],
    'css': [],
    'installable': True,
    'auto_install': False,
    'application': True,
}
