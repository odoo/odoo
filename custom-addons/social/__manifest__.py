# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Social Marketing',
    'category': 'Marketing/Social Marketing',
    'sequence': 175,
    'summary': 'Manage your social media and website visitors',
    'version': '1.3',
    'description': """Manage your social media and website visitors""",
    'website': 'https://www.odoo.com/app/social-marketing',
    'depends': ['web', 'mail', 'iap', 'link_tracker'],
    'data': [
        'security/social_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/social_menu_views.xml',
        'views/social_account_views.xml',
        'views/social_live_post_views.xml',
        'views/social_media_views.xml',
        'views/social_post_template_views.xml',
        'views/social_post_views.xml',
        'views/social_stream_post_views.xml',
        'views/social_stream_views.xml',
        'views/res_config_settings_views.xml',
        'views/utm_campaign_views.xml',
        'views/social_templates.xml'
    ],
    'demo': [
        'data/social_demo.xml'
    ],
    'application': True,
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'social/static/src/js/fields/*',
            'social/static/src/js/add_stream_modal.js',
            'social/static/src/js/images_carousel_dialog.js',
            'social/static/src/js/post_kanban_view.js',
            'social/static/src/js/social_post_formatter_mixin.js',
            'social/static/src/js/social_post_preview_field.js',
            'social/static/src/js/stream_post_comment.js',
            'social/static/src/js/stream_post_comment_list.js',
            'social/static/src/js/stream_post_comments.js',
            'social/static/src/js/stream_post_comments_reply.js',
            'social/static/src/js/stream_post_kanban_controller.js',
            'social/static/src/js/stream_post_kanban_dashboard.js',
            'social/static/src/js/stream_post_kanban_model.js',
            'social/static/src/js/stream_post_kanban_record.js',
            'social/static/src/js/stream_post_kanban_refresh_banner.js',
            'social/static/src/js/stream_post_kanban_renderer.js',
            'social/static/src/js/stream_post_kanban_view.js',
            'social/static/src/js/tours/social.js',
            'social/static/src/scss/social.scss',
            'social/static/src/xml/**/*',
        ],
    },
    'license': 'OEEL-1',
}
