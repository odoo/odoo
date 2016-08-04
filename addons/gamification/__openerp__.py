# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Gamification',
    'sequence': 160,
    'category': 'Human Resources',
    'website' : 'https://www.odoo.com/page/gamification',
    'depends': ['mail', 'web_kanban_gauge'],
    'description': """
Gamification process
====================
The Gamification module provides ways to evaluate and motivate the users of Odoo.

The users can be evaluated using goals and numerical objectives to reach.
**Goals** are assigned through **challenges** to evaluate and compare members of a team with each others and through time.

For non-numerical achievements, **badges** can be granted to users. From a simple "thank you" to an exceptional achievement, a badge is an easy way to exprimate gratitude to a user for their good work.

Both goals and badges are flexibles and can be adapted to a large range of modules and actions. When installed, this module creates easy goals to help new users to discover Odoo and configure their user profile.
""",
    'data': [
        'security/gamification_security.xml',
        'security/ir.model.access.csv',
        'wizard/grant_badge_views.xml',
        'views/badge_views.xml',
        'views/challenge_views.xml',
        'views/goal_views.xml',
        'data/cron_data.xml',
        'data/goal_base_data.xml',
        'data/badge_data.xml',
        'views/gamification_templates.xml',
    ],
}
