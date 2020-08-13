# -*- coding: utf-8 -*-
{
    'name': 'eLearning',
    'version': '2.2',
    'sequence': 125,
    'summary': 'Manage and publish an eLearning platform',
    'website': 'https://www.odoo.com/page/slides',
    'category': 'Website/eLearning',
    'description': """
Create Online Courses
=====================

Featuring

 * Integrated course and lesson management
 * Fullscreen navigation
 * Support Youtube videos, Google documents, PDF, images, web pages
 * Test knowledge with quizzes
 * Filter and Tag
 * Statistics
""",
    'depends': [
        'portal_rating',
        'website',
        'website_mail',
        'website_profile',
    ],
    'data': [
        'security/website_slides_security.xml',
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/rating_rating_views.xml',
        'views/slide_question_views.xml',
        'views/slide_slide_views.xml',
        'views/slide_channel_partner_views.xml',
        'views/slide_channel_views.xml',
        'views/slide_channel_tag_views.xml',
        'views/website_slides_menu_views.xml',
        'views/website_slides_templates_homepage.xml',
        'views/website_slides_templates_course.xml',
        'views/website_slides_templates_lesson.xml',
        'views/website_slides_templates_lesson_fullscreen.xml',
        'views/website_slides_templates_lesson_embed.xml',
        'views/website_slides_templates_profile.xml',
        'views/website_slides_templates_utils.xml',
        'wizard/slide_channel_invite_views.xml',
        'data/gamification_data.xml',
        'data/mail_data.xml',
        'data/mail_activity_data.xml',
        'data/slide_data.xml',
        'data/website_data.xml',
    ],
    'demo': [
        'data/res_users_demo.xml',
        'data/slide_channel_tag_demo.xml',
        'data/slide_channel_demo.xml',
        'data/slide_slide_demo.xml',
        'data/slide_user_demo.xml',
    ],
    'qweb': [
        'static/src/xml/activity.xml',
    ],
    'installable': True,
    'application': True,
}
