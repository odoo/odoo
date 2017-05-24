# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo RTL support
#    Copyright (C) 2014 Mohammed Barsi.
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
    'name': 'Web RTL',
    'version': '1.0',
    'author': 'Mohammed Barsi',
    'sequence': 4,
    'summary': 'Web RTL(Right to Left) layout',
    'description':
        """
Adding RTL(Right to Left) Support for Odoo.
===========================================

This module provides an RTL support for Odoo backend.
        """,
    'depends': ['web'],
    'auto_install': False,
    'data': [
        'views/templates.xml',
    ],
}
