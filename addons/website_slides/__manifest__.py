# -*- coding: utf-8 -*-
{
    'name': 'Slides',
    'version': '1.0',
    'sequence': 145,
    'summary': 'Publish videos, slides and documents',
    'website': 'https://www.odoo.com/page/slides',
    'category': 'Website',
    'description': """
Share and Publish Videos, Presentations and Documents'
======================================================

 * Website Application
 * Channel Management
 * Filters and Tagging
 * Statistics of Presentation
 * Channel Subscription
 * Supported document types : PDF, images, YouTube videos and Google Drive documents)
""",
    'depends': [
        'website',
        'website_mail',
        'website_profile',
        'website_rating'],
    'data': [
        'views/assets.xml',
        'views/res_config_settings_views.xml',
        'views/slide_slide_views.xml',
        'views/slide_channel_partner_views.xml',
        'views/slide_channel_views.xml',
        'views/slide_channel_tag_views.xml',
        'views/website_slides_menu_views.xml',
        'views/website_slides_templates_homepage.xml',
        'views/website_slides_templates_course.xml',
        'views/website_slides_templates_lesson.xml',
        'views/website_slides_templates_lesson_embed.xml',
        'views/website_slides_templates_profile.xml',
        'views/website_slides_templates_utils.xml',
        'wizard/slide_channel_invite_views.xml',
        'data/ir_data.xml',
        'data/gamification_data.xml',
        'data/mail_data.xml',
        'data/slide_data.xml',
        'data/website_data.xml',
        'security/ir.model.access.csv',
        'security/website_slides_security.xml'
    ],
    'demo': [
        'data/slide_channel_tag_demo.xml',
        'data/slide_channel_demo.xml',
        'data/slide_slide_demo.xml',
        'data/slide_user_demo.xml',
    ],
    'installable': True,
    'application': True,
}
