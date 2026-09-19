{
    "name": "Gamification",
    "version": "1.4",
    "category": "Productivity",
    "sequence": 160,
    "description": """
Gamification process
====================
The Gamification module provides ways to evaluate and motivate the users of Odoo.

The users can be evaluated using goals and numerical objectives to reach.
**Goals** are assigned through **challenges** to evaluate and compare members of a team with each others and through time.

For non-numerical achievements, **badges** can be granted to users. From a simple "thank you" to an exceptional achievement, a badge is an easy way to express gratitude to a user for their good work.

Both goals and badges are flexible and can be adapted to a large range of modules and actions. When installed, this module creates easy goals to help new users to discover Odoo and configure their user profile.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mail",
    ],
    "data": [
        "security/res_groups_security.xml",
        "wizards/update_goal.xml",
        "wizards/grant_badge.xml",
        "views/res_users_views.xml",
        "views/gamification_karma_rank_views.xml",
        "views/gamification_karma_tracking_views.xml",
        "views/gamification_badge_views.xml",
        "views/gamification_badge_user_views.xml",
        "views/gamification_goal_views.xml",
        "views/gamification_goal_definition_views.xml",
        "views/gamification_challenge_views.xml",
        "views/gamification_challenge_line_views.xml",
        "views/gamification_streak_views.xml",
        "views/gamification_kudos_views.xml",
        "views/gamification_achievement_views.xml",
        "views/gamification_team_views.xml",
        "views/gamification_engagement_views.xml",
        "views/gamification_activity_views.xml",
        "views/gamification_mentorship_views.xml",
        "views/gamification_quest_views.xml",
        "views/gamification_season_views.xml",
        "views/gamification_skill_views.xml",
        "views/gamification_menus.xml",
        "security/gamification_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "data/mail_template_data.xml",
        "data/gamification_badge_data.xml",
        "data/gamification_challenge_data.xml",
        "data/gamification_kudos_data.xml",
        "data/gamification_karma_rank_data.xml",
    ],
    "demo": [
        "demo/gamification_karma_rank_demo.xml",
        "demo/gamification_karma_tracking_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "gamification/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "gamification/static/tests/**/*",
        ],
    },
    "application": True,
}
