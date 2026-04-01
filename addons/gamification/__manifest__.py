# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Gamification',
    'version': '1.0',
    'sequence': 160,
    'category': 'Human Resources',
    'depends': ['mail'],
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
        'views/res_users_views.xml',
        'views/gamification_karma_rank_views.xml',
        'views/gamification_karma_tracking_views.xml',
        'views/gamification_badge_views.xml',
        'views/gamification_badge_user_views.xml',
        'views/gamification_goal_views.xml',
        'views/gamification_goal_definition_views.xml',
        'views/gamification_challenge_views.xml',
        'views/gamification_challenge_line_views.xml',
        'views/gamification_menus.xml',
        'security/gamification_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',  # keep before to populate challenge reports
        'data/gamification_badge_data.xml',
        'data/gamification_challenge_data.xml',
        'data/gamification_karma_rank_data.xml',
    ],
    'demo': [
        'data/gamification_karma_rank_demo.xml',
        'data/gamification_karma_tracking_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'gamification/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
