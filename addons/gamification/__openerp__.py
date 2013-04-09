# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2013 Tiny SPRL (<http://openerp.com>).
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
    'depends': ['mail'],
    'description': """
Gamification process
====================
The Gamification module provide ways to evaluate and motivate the users of OpenERP.
The two main functions are goals and badges.

Goals
-----
A **Goal** is an objective applied to an user with a numerical target to reach. It can have starting and end date. Users usually do not create goals but relies on goal plans.

A **Goal Type** is a generic objective that can be applied to any structure stored in the database and use numerical value. The creation of goal types is quite technical and should rarely be done. Once a generic goal is created, it can be associated to several goal plans with different numerical targets.

A **Goal Plan** is a a set of goal types with a target value to reach applied to a group of users. It can be periodic to create and evaluate easily the performances of a team.

Badges
------
A **Badge** is a symbolic token granted to a user as a sign of reward. It can be offered by a user to another or automatically offered when some conditions are met. The conditions can either be a list of goal types succeeded or a user definied python code executed.

""",

    'data': [
        'plan_view.xml',
        'badge_view.xml',
        'goal_view.xml',
        'cron.xml',
        'security/gamification_security.xml',
        'security/ir.model.access.csv',
        'goal_base_data.xml',
        'badge_data.xml',
    ],
    'test': [
        'test/goal_demo.yml'
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'css': ['static/src/css/goal.css'],
    'js': [
        'static/src/js/gamification.js',
        'static/src/js/justgage.js',
    ],
    'qweb': ['static/src/xml/gamification.xml'],
}
