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
    'name': 'HR Gamification',
    'version': '1.0',
    'author': 'OpenERP SA',
    'category': 'hidden',
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['gamification', 'hr'],
    'description': """Use the HR ressources for the gamification process.

The HR officer can now manage challenges and badges.
This allow the user to send badges to employees instead of simple users.
Badge received are displayed on the user profile.
""",
    'data': [
        'security/ir.model.access.csv',
        'security/gamification_security.xml',
        'wizard/grant_badge.xml',
        'views/gamification.xml',
        'views/hr_gamification.xml',
    ],
    'auto_install': True,
}
