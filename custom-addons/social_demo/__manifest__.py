# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Social Demo Module',
    'category': 'Hidden',
    'summary': 'Get demo data for the social module',
    'version': '1.0',
    'description': """Get demo data for the social module.
    This module creates a social 'sandbox' where you can play around with the social app without publishing anything on actual social media.""",
    'depends': ['social', 'social_facebook', 'social_twitter', 'social_linkedin', 'social_youtube', 'social_instagram', 'product'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/social_demo.xml',
        'data/social_demo_facebook.xml',
        'data/social_demo_linkedin.xml',
        'data/social_demo_instagram.xml',
        'data/social_demo_twitter.xml',
        'data/social_demo_youtube.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'social_demo/static/src/js/social_youtube_upload_field.js',
            'social_demo/static/src/js/stream_post_comment.js',
            'social_demo/static/src/js/stream_post_comments_reply.js',
        ],
    },
    'license': 'OEEL-1',
}
