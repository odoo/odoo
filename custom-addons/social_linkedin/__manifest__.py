# -*- coding: utf-8 -*-
{
    'name': 'Social LinkedIn',
    'summary': 'Manage your LinkedIn accounts and schedule posts',
    'description': 'Manage your LinkedIn accounts and schedule posts',
    'category': 'Marketing/Social Marketing',
    'version': '0.1',
    'depends': ['social', 'iap'],
    'data': [
        'data/social_media_data.xml',
        'views/social_post_template_views.xml',
        'views/social_linkedin_preview.xml',
        'views/social_stream_posts_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'social_linkedin/static/src/js/stream_post_comment.js',
            'social_linkedin/static/src/js/stream_post_comment_list.js',
            'social_linkedin/static/src/js/stream_post_comments.js',
            'social_linkedin/static/src/js/stream_post_comments_reply.js',
            'social_linkedin/static/src/js/stream_post_kanban_record.js',
            ('after', 'social/static/src/js/social_post_formatter_mixin.js', 'social_linkedin/static/src/js/social_post_formatter_mixin.js'),
            'social_linkedin/static/src/scss/social_linkedin.scss',
            'social_linkedin/static/src/xml/**/*',
        ],
        'web.assets_web_dark': [
            'social_linkedin/static/src/scss/social_linkedin.dark.scss',
        ],
    },
    'license': 'OEEL-1',
}
