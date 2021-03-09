# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Forum',
    'category': 'Website/Website',
    'sequence': 265,
    'summary': 'Manage a forum with FAQ and Q&A',
    'version': '1.1',
    'description': """
Ask questions, get answers, no distractions
        """,
    'website': 'https://www.odoo.com/page/community-builder',
    'depends': [
        'auth_signup',
        'website_mail',
        'website_profile',
    ],
    'data': [
        'data/forum_default_faq.xml',
        'data/forum_data.xml',
        'data/mail_data.xml',
        'data/mail_templates.xml',
        'views/forum.xml',
        'views/res_users_views.xml',
        'views/website_forum.xml',
        'views/website_forum_profile.xml',
        'views/ir_qweb.xml',
        'security/ir.model.access.csv',
        'security/website_forum_security.xml',
        'data/badges_question.xml',
        'data/badges_answer.xml',
        'data/badges_participation.xml',
        'data/badges_moderation.xml',
    ],
    'demo': [
        'data/forum_demo.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {
        'website.assets_editor': [
            # inside .
            'website_forum/static/src/js/tours/website_forum.js',
            # inside .
            'website_forum/static/src/js/website_forum.editor.js',
        ],
        'web.assets_tests': [
            # inside .
            'website_forum/static/tests/tours/website_forum_question.js',
        ],
        'web.assets_frontend': [
            # after link[last()]
            'website_forum/static/src/scss/website_forum.scss',
            # after script[last()]
            'website_forum/static/src/js/website_forum.js',
            # after script[last()]
            'website_forum/static/src/js/website_forum.share.js',
        ],
        'web.assets_qweb': [
            'website_forum/static/src/xml/*.xml',
        ],
    }
}
