# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Gamification',
    'version': '1.0',
    'sequence': 160,
    'category': 'Human Resources',
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
        'data/gamification_karma_rank_data.xml',
        'views/gamification.xml',
        'views/gamification_karma_rank_views.xml',
        'views/gamification_karma_tracking_views.xml',
        'views/mail_templates.xml',
        'views/res_users_views.xml',
    ],
    'demo': [
        'data/gamification_karma_rank_demo.xml',
        'data/gamification_karma_tracking_demo.xml',
    ],
}
