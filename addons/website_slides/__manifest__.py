# -*- coding: utf-8 -*-
{
    'name': 'eLearning',
    'version': '2.4',
    'sequence': 125,
    'summary': 'Manage and publish an eLearning platform',
    'website': 'https://www.odoo.com/app/elearning',
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
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'views/rating_rating_views.xml',
        'views/slide_question_views.xml',
        'views/slide_slide_views.xml',
        'views/slide_channel_partner_views.xml',
        'views/slide_channel_views.xml',
        'views/slide_channel_tag_views.xml',
        'views/slide_snippets.xml',
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
        'data/mail_template_data.xml',
        'data/mail_templates.xml',
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
    'installable': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'website_slides/static/src/scss/rating_rating_views.scss',
            'website_slides/static/src/scss/slide_views.scss',
            'website_slides/static/src/components/activity/activity.js',
            'website_slides/static/src/js/slide_category_one2many.js',
            'website_slides/static/src/js/rating_field_backend.js',
        ],
        'web.assets_frontend': [
            'website_slides/static/src/scss/website_slides.scss',
            'website_slides/static/src/scss/website_slides_profile.scss',
            'website_slides/static/src/scss/slides_slide_fullscreen.scss',
            'website_slides/static/src/js/slides.js',
            'website_slides/static/src/js/slides_share.js',
            'website_slides/static/src/js/slides_upload.js',
            'website_slides/static/src/js/slides_category_add.js',
            'website_slides/static/src/js/slides_category_delete.js',
            'website_slides/static/src/js/slides_slide_archive.js',
            'website_slides/static/src/js/slides_slide_toggle_is_preview.js',
            'website_slides/static/src/js/slides_slide_like.js',
            'website_slides/static/src/js/slides_course_slides_list.js',
            'website_slides/static/src/js/slides_course_fullscreen_player.js',
            'website_slides/static/src/js/slides_course_join.js',
            'website_slides/static/src/js/slides_course_enroll_email.js',
            'website_slides/static/src/js/slides_course_quiz.js',
            'website_slides/static/src/js/slides_course_quiz_question_form.js',
            'website_slides/static/src/js/slides_course_quiz_finish.js',
            'website_slides/static/src/js/slides_course_tag_add.js',
            'website_slides/static/src/js/slides_course_unsubscribe.js',
            'website_slides/static/src/js/tours/slides_tour.js',
            'website_slides/static/src/js/portal_chatter.js',
        ],
        'web.assets_tests': [
            'website_slides/static/src/tests/**/*',
        ],
        'website.assets_editor': [
            'website_slides/static/src/js/website_slides.editor.js',
        ],
        'website_slides.slide_embed_assets': [
            ('include', 'web._assets_helpers'),
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap'),
            'website_slides/static/src/scss/website_slides.scss',
            ('include', 'web.pdf_js_lib'),
            'website_slides/static/lib/pdfslidesviewer/PDFSlidesViewer.js',
            'website_slides/static/src/js/slides_embed.js',
        ],
        'web.qunit_suite_tests': [
            'website_slides/static/src/components/activity/activity_tests.js',
        ],
        'web.assets_qweb': [
            'website_slides/static/src/components/activity/activity.xml',
        ],
    },
    'license': 'LGPL-3',
}
