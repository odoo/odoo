# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Social Instagram',
    'category': 'Social',
    'summary': 'Manage your Instagram Business accounts and schedule posts',
    'version': '1.0',
    'description': """Manage your Instagram Business accounts and schedule posts.""",
    'depends': ['social'],
    'data': [
        'data/social_media_data.xml',
        'views/social_instagram_templates.xml',
        'views/social_post_template_views.xml',
        'views/social_stream_post_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'social_instagram/static/src/js/stream_post_comment.js',
            'social_instagram/static/src/js/stream_post_comment_list.js',
            'social_instagram/static/src/js/stream_post_comments.js',
            'social_instagram/static/src/js/stream_post_comments_reply.js',
            'social_instagram/static/src/js/stream_post_kanban_dashboard.js',
            'social_instagram/static/src/js/stream_post_kanban_record.js',
            ('after', 'social/static/src/js/social_post_formatter_mixin.js', 'social_instagram/static/src/js/social_post_formatter_mixin.js'),
            'social_instagram/static/src/scss/social_instagram.scss',
            'social_instagram/static/src/xml/**/*',
        ],
    },
    'license': 'OEEL-1',
}
