# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Social Facebook',
    'category': 'Marketing/Social Marketing',
    'summary': 'Manage your Facebook pages and schedule posts',
    'version': '1.0',
    'description': """Manage your Facebook pages and schedule posts""",
    'depends': ['social'],
    'data': [
        'data/social_media_data.xml',
        'views/social_facebook_templates.xml',
        'views/social_post_template_views.xml',
        'views/social_stream_post_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'social_facebook/static/src/js/stream_post_comment.js',
            'social_facebook/static/src/js/stream_post_comment_list.js',
            'social_facebook/static/src/js/stream_post_comments.js',
            'social_facebook/static/src/js/stream_post_comments_reply.js',
            'social_facebook/static/src/js/stream_post_kanban_record.js',
            ('after', 'social/static/src/js/social_post_formatter_mixin.js', 'social_facebook/static/src/js/social_post_formatter_mixin.js'),
            'social_facebook/static/src/scss/social_facebook.scss',
            'social_facebook/static/src/xml/**/*',
        ],
        'web.assets_web_dark': [
            'social_facebook/static/src/scss/social_facebook.dark.scss',
        ],
        'web.qunit_suite_tests': [
            'social_facebook/static/src/js/tests/**/*',
        ],
    },
    'license': 'OEEL-1',
}
