# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP SA (<http://openerp.com>).
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
    'name': 'Portal Gamification',
    'version': '1',
    'category': 'Tools',
    'complexity': 'easy',
    'description': """
This module adds security rules for gamification to allow portal users to participate to challenges
===================================================================================================
    """,
    'author': 'OpenERP SA',
    'depends': ['gamification','portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/portal_security.xml',
    ],
    'installable': True,
    'auto_install': True,
    'category': 'Hidden',
}

