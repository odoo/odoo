# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Forum',
    'category': 'Website/Website',
    'sequence': 265,
    'summary': 'Manage a forum with FAQ and Q&A',
    'version': '1.2',
    'description': """
Ask questions, get answers, no distractions
        """,
    'website': 'https://www.odoo.com/app/forum',
    'depends': [
        'auth_signup',
        'website_mail',
        'website_profile',
    ],
    'data': [
        'data/ir_config_parameter_data.xml',
        'data/forum_forum_template_faq.xml',
        'data/forum_forum_data.xml',
        'data/forum_post_reason_data.xml',
        'data/ir_actions_data.xml',
        'data/mail_message_subtype_data.xml',
        'data/mail_templates.xml',
        'data/website_menu_data.xml',
        'data/website_forum_tour.xml',

        'views/forum_post_views.xml',
        'views/forum_post_reason_views.xml',
        'views/forum_tag_views.xml',
        'views/forum_forum_views.xml',
        'views/res_users_views.xml',
        'views/gamification_karma_tracking_views.xml',
        'views/forum_menus.xml',

        'views/base_contact_templates.xml',
        'views/forum_forum_templates.xml',
        'views/forum_forum_templates_forum_all.xml',
        'views/forum_forum_templates_layout.xml',
        'views/forum_forum_templates_moderation.xml',
        'views/forum_forum_templates_post.xml',
        'views/forum_forum_templates_tools.xml',
        'views/forum_templates_mail.xml',
        'views/website_profile_templates.xml',
        'views/snippets/snippets.xml',

        'security/ir.model.access.csv',
        'security/ir_rule_data.xml',

        'data/gamification_badge_data_question.xml',
        'data/gamification_badge_data_answer.xml',
        'data/gamification_badge_data_participation.xml',
        'data/gamification_badge_data_moderation.xml',
    ],
    'demo': [
        'data/forum_tag_demo.xml',
        'data/forum_post_demo.xml',
    ],
    'installable': True,
    'assets': {
        'website.assets_editor': [
            'website_forum/static/src/js/systray_items/*.js',
        ],
        'web.assets_tests': [
            'website_forum/static/tests/**/*',
        ],
        'web.assets_backend': [
            'website_forum/static/src/js/tours/website_forum.js',
        ],
        'web.assets_frontend': [
            'website_forum/static/src/js/tours/website_forum.js',
            'website_forum/static/src/scss/website_forum.scss',
            'website_forum/static/src/js/website_forum.js',
            'website_forum/static/src/js/website_forum.share.js',
            'website_forum/static/src/xml/public_templates.xml',
            'website_forum/static/src/xml/website_forum_tags_wrapper.xml',
            'website_forum/static/src/components/flag_mark_as_offensive/**/*',
        ],
    },
    'license': 'LGPL-3',
}
