# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Gamification Quizzes',
    'category': 'Marketing/Events',
    'sequence': 1000,
    'version': '1.0',
    'summary': 'Gamification quizzes and leaderboard',
    'website': 'https://www.odoo.com/page/events',
    'description': "",
    'depends': [
        'gamification',
        'website_profile',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/quiz_question_views.xml',
        'views/quiz_templates.xml'
    ],
    'demo': [
    ],
    'application': False,
    'installable': True,
}
