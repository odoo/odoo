# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Social Push Notifications',
    'category': 'Marketing/Social Marketing',
    'summary': 'Send live notifications to your web visitors',
    'version': '1.1',
    'description': """Send live notifications to your web visitors""",
    'depends': ['social', 'website'],
    'external_dependencies': {
        'python': ['google_auth'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/social_post_template_views.xml',
        'views/social_post_views.xml',
        'views/res_config_settings_views.xml',
        'views/social_push_notifications_templates.xml',
        'views/website_visitor_views.xml',
        'views/utm_campaign_views.xml',
        'data/social_media_data.xml',
    ],
    'auto_install': True,
    'post_init_hook': '_create_social_accounts',
    'assets': {
        'web.assets_frontend': [
            'social_push_notifications/static/lib/firebase-app-6.3.4.js',
            'social_push_notifications/static/lib/firebase-messaging-6.3.4.js',
            'social_push_notifications/static/src/js/push_notification_request_popup.js',
            'social_push_notifications/static/src/js/push_notification_widget.js',
            'social_push_notifications/static/src/scss/social_push_notifications_frontend.scss',
            'social_push_notifications/static/src/xml/social_push_notifications_templates.xml',
        ],
        'web.assets_backend': [
            'social_push_notifications/static/src/scss/social_push_notifications.scss',
        ],
    },
    'license': 'OEEL-1',
}
