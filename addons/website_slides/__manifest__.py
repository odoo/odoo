# -*- coding: utf-8 -*-
{
    'name': 'eLearning',
    'version': '2.3',
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
            # inside .
            'website_slides/static/src/scss/rating_rating_views.scss',
            # inside .
            'website_slides/static/src/scss/slide_views.scss',
            # inside .
            'website_slides/static/src/components/activity/activity.js',
            # inside .
            'website_slides/static/src/js/slide_category_one2many.js',
            # inside .
            'website_slides/static/src/js/rating_field_backend.js',
        ],
        'web.assets_frontend': [
            # after //link[last()]
            'website_slides/static/src/scss/website_slides.scss',
            # after //link[last()]
            'website_slides/static/src/scss/website_slides_profile.scss',
            # after //link[last()]
            'website_slides/static/src/scss/slides_slide_fullscreen.scss',
            # after //script[last()]
            'website_slides/static/src/js/slides.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_share.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_upload.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_category_add.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_category_delete.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_slide_archive.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_slide_toggle_is_preview.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_slide_like.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_course_slides_list.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_course_fullscreen_player.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_course_join.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_course_enroll_email.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_course_quiz.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_course_quiz_question_form.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_course_quiz_finish.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_course_tag_add.js',
            # after //script[last()]
            'website_slides/static/src/js/slides_course_unsubscribe.js',
            # after //script[last()]
            'website_slides/static/src/js/tours/slides_tour.js',
            # after //script[last()]
            'website_slides/static/src/js/portal_chatter.js',
        ],
        'web.assets_tests': [
            # inside .
            'website_slides/static/src/tests/tours/slides_tour_tools.js',
            # inside .
            'website_slides/static/src/tests/tours/slides_course_member.js',
            # inside .
            'website_slides/static/src/tests/tours/slides_course_member_yt.js',
            # inside .
            'website_slides/static/src/tests/tours/slides_course_publisher.js',
        ],
        'website.assets_editor': [
            # inside .
            'website_slides/static/src/js/website_slides.editor.js',
        ],
        'website_slides.slide_embed_assets': [
            # None None
            ('include', 'web._assets_helpers'),
            # new asset template 
            'web/static/lib/bootstrap/scss/_variables.scss',
            # None None
            ('include', 'web._assets_bootstrap'),
            # new asset template 
            'website_slides/static/src/scss/website_slides.scss',
            # None None
            ('include', 'web.pdf_js_lib'),
            # new asset template 
            'website_slides/static/lib/pdfslidesviewer/PDFSlidesViewer.js',
            # new asset template 
            'website_slides/static/src/js/slides_embed.js',
        ],
        'web.qunit_suite_tests': [
            # after //script[last()]
            'website_slides/static/src/components/activity/activity_tests.js',
        ],
        'web.assets_qweb': [
            'website_slides/static/src/components/activity/activity.xml',
        ],
    }
}
