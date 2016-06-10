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
    'name': 'Gamification',
    'version': '1.0',
    'author': 'OpenERP SA',
    'category': 'Human Resources',
    'website' : 'https://www.odoo.com/page/gamification',
    'depends': ['mail', 'email_template', 'web_kanban_gauge'],
    'description': """
Gamification process
====================
The Gamification module provides ways to evaluate and motivate the users of OpenERP.

The users can be evaluated using goals and numerical objectives to reach.
**Goals** are assigned through **challenges** to evaluate and compare members of a team with each others and through time.

For non-numerical achievements, **badges** can be granted to users. From a simple "thank you" to an exceptional achievement, a badge is an easy way to exprimate gratitude to a user for their good work.

Both goals and badges are flexibles and can be adapted to a large range of modules and actions. When installed, this module creates easy goals to help new users to discover OpenERP and configure their user profile.
""",

    'data': [
        'wizard/update_goal.xml',
        'wizard/grant_badge.xml',
        'views/badge.xml',
        'views/challenge.xml',
        'views/goal.xml',
        'data/cron.xml',
        'security/gamification_security.xml',
        'security/ir.model.access.csv',
        'data/goal_base.xml',
        'data/badge.xml',
        'views/gamification.xml',
    ],
    'application': True,
    'auto_install': False,
    'qweb': ['static/src/xml/gamification.xml'],
}
