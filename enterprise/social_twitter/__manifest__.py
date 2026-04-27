# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Social X',
    'category': 'Marketing/Social Marketing',
    'summary': 'Manage your X accounts and schedule posts',
    'version': '1.1',
    'description': """Manage your X accounts and schedule posts""",
    'depends': ['social', 'iap'],
    'data': [
        'security/ir.model.access.csv',
        'data/social_media_data.xml',
        'views/social_post_template_views.xml',
        'views/social_stream_views.xml',
        'views/social_stream_post_views.xml',
        'views/social_twitter_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'social_twitter/static/src/scss/social_twitter.scss',
            'social_twitter/static/src/js/stream_post_comment.js',
            'social_twitter/static/src/js/stream_post_comment_list.js',
            'social_twitter/static/src/js/stream_post_comments.js',
            'social_twitter/static/src/js/stream_post_comments_reply.js',
            'social_twitter/static/src/js/stream_post_comments_reply_quote.js',
            'social_twitter/static/src/js/stream_post_kanban_record.js',
            'social_twitter/static/src/js/stream_post_twitter_quote.js',
            'social_twitter/static/src/js/twitter_users_autocomplete.js',
            ('after', 'social/static/src/js/social_post_formatter_mixin.js', 'social_twitter/static/src/js/social_post_formatter_mixin.js'),
            'social_twitter/static/src/xml/**/*',
        ],
        'web.assets_web_dark': [
            'social_twitter/static/src/scss/social_twitter.dark.scss',
        ],
        'web.assets_tests': [
            'social_twitter/static/tests/tours/tour_social_twitter_spam.js',
        ],
    },
    'license': 'OEEL-1',
}
